# app/routes/admin.py
from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List, Dict, Optional
import json
import redis
import time
from datetime import datetime

from ..services.session import r as redis_client, get_client_ip, rate_limit
from ..config import get_config
from ..utils.logging import get_logger

# ------------------------------------------------------------------ #
# Config
# ------------------------------------------------------------------ #
config = get_config()
logger = get_logger(__name__)

router = APIRouter()

# ------------------------------------------------------------------ #
# Admin Auth (simple API key for now – replace with JWT later)
# ------------------------------------------------------------------ #
ADMIN_API_KEY = config.security.admin_api_key

def verify_admin(request: Request):
    api_key = request.headers.get("x-admin-key")
    if api_key != ADMIN_API_KEY:
        raise HTTPException(403, "Invalid admin key")
    return True

# ------------------------------------------------------------------ #
# Helper: Get all active session IDs
# ------------------------------------------------------------------ #
def get_active_sessions() -> List[Dict]:
    keys = redis_client.keys("session:*")
    sessions = []
    for key in keys:
        key_str = key.decode()
        session_id = key_str.split(":", 1)[1]
        ttl = redis_client.ttl(key_str)
        if ttl > 0:
            # Get last message timestamp
            last_msg = redis_client.lindex(key_str, -1)
            last_time = None
            if last_msg:
                try:
                    role, content = last_msg.decode().split(":", 1)
                    # You can store timestamps later; for now, use Redis TTL
                except:
                    pass
            sessions.append({
                "session_id": session_id,
                "last_activity": int(time.time() - (86400 - ttl)),  # approx
                "ttl_seconds": ttl,
                "message_count": redis_client.llen(key_str)
            })
    # Sort by last activity
    sessions.sort(key=lambda x: x["last_activity"], reverse=True)
    return sessions

# ------------------------------------------------------------------ #
# 1. List all active sessions
# ------------------------------------------------------------------ #
@router.get("/admin/sessions")
async def list_sessions(_: bool = Depends(verify_admin)):
    return {"sessions": get_active_sessions()}

# ------------------------------------------------------------------ #
# 2. Get full chat history of a session
# ------------------------------------------------------------------ #
@router.get("/admin/session/{session_id}")
async def get_session_history(session_id: str, _: bool = Depends(verify_admin)):
    key = f"session:{session_id}"
    if not redis_client.exists(key):
        raise HTTPException(404, "Session not found")

    history = redis_client.lrange(key, 0, -1)
    messages = []
    for item in history:
        try:
            role, content = item.decode("utf-8").split(":", 1)
            messages.append({"role": role, "content": content})
        except:
            continue
    return {"session_id": session_id, "messages": messages}

# ------------------------------------------------------------------ #
# 3. Admin joins a session (SSE stream for real-time updates)
# ------------------------------------------------------------------ #
@router.get("/admin/session/{session_id}/stream")
async def admin_stream_session(request: Request, session_id: str, _: bool = Depends(verify_admin)):
    key = f"session:{session_id}"
    if not redis_client.exists(key):
        raise HTTPException(404, "Session not found")

    async def event_generator():
        last_index = redis_client.llen(key)
        yield f"data: {json.dumps({'type': 'init', 'messages': []})}\n\n"

        while True:
            if await request.is_disconnected():
                break

            current_len = redis_client.llen(key)
            if current_len > last_index:
                new_msgs = redis_client.lrange(key, last_index, -1)
                for msg in new_msgs:
                    try:
                        role, content = msg.decode("utf-8").split(":", 1)
                        yield f"data: {json.dumps({'type': 'message', 'role': role, 'content': content})}\n\n"
                    except:
                        continue
                last_index = current_len

            await asyncio.sleep(0.5)

    import asyncio
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# ------------------------------------------------------------------ #
# 4. Admin sends message to user (pushes to user's session)
# ------------------------------------------------------------------ #
@router.post("/admin/session/{session_id}/send")
async def admin_send_message(
    session_id: str,
    body: Dict,
    _: bool = Depends(verify_admin)
):
    message = body.get("message", "").strip()
    if not message:
        raise HTTPException(400, "Message required")

    key = f"session:{session_id}"
    if not redis_client.exists(key):
        raise HTTPException(404, "Session not found")

    # Store as admin message
    redis_client.rpush(key, f"admin:{message}")
    redis_client.expire(key, 86400)

    # Optional: publish to pub/sub so user client can receive instantly
    redis_client.publish(f"session:{session_id}", json.dumps({
        "role": "admin",
        "content": message
    }))

    return {"status": "sent", "message": message}