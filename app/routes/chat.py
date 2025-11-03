from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import json
import redis
import os

from ..services.session import (
    get_session, create_session_id, sign_session,
    get_client_ip, rate_limit, r as redis_client
)
from ..services.search import search_products, contains_gpu
from ..services.ollama import stream_ollama_response

router = APIRouter()

# ------------------------------------------------------------------ #
# Models
# ------------------------------------------------------------------ #
class ChatRequest(BaseModel):
    message: str
    user_info: Optional[dict] = None

class HumanRequest(BaseModel):
    name: str
    email: str

# ------------------------------------------------------------------ #
# Nonsense detection
# ------------------------------------------------------------------ #
def is_nonsense(text: str) -> bool:
    words = text.lower().split()
    if len(words) < 2:
        return True
    return len(set(words)) / len(words) < 0.3

# ------------------------------------------------------------------ #
# Routes
# ------------------------------------------------------------------ #
@router.get("/session")
async def init_session(response: JSONResponse):
    sid = create_session_id()
    sig = sign_session(sid)

    is_dev = os.getenv("ENV", "dev") == "dev"
    secure = not is_dev
    samesite = "lax" if is_dev else "none"

    response.set_cookie(key="session_id", value=sid, httponly=True,
                        secure=secure, samesite=samesite, path="/")
    response.set_cookie(key="session_sig", value=sig, httponly=True,
                        secure=secure, samesite=samesite, path="/")
    return {"session_id": sid}


@router.post("/chat")
async def chat(
    request: Request,
    body: ChatRequest,
    session_id: str = Depends(get_session)
):
    ip = get_client_ip(request)

    if not rate_limit(ip):
        raise HTTPException(429, "Too many requests. Wait 1 minute.")

    if is_nonsense(body.message):
        raise HTTPException(400, "Please send a meaningful message.")

    if contains_gpu(body.message):
        return JSONResponse({
            "response": "We only sell cables and cable-related accessories. We do **not** sell GPUs or graphics cards.",
            "session_id": session_id,
            "suggested_products": None
        })

    products = search_products(body.message)

    # Load history
    key = f"session:{session_id}"
    history = redis_client.lrange(key, 0, -1)
    messages: List[Dict] = []
    for item in history:
        role, content = item.decode("utf-8").split(":", 1)
        messages.append({"role": role, "content": content})

    # Append user message
    user_msg = {"role": "user", "content": body.message}
    messages.append(user_msg)
    redis_client.rpush(key, f"{user_msg['role']}:{user_msg['content']}")
    redis_client.expire(key, 86400)

    # ------------------------------------------------------------------ #
    # Streaming generator
    # ------------------------------------------------------------------ #
    async def event_generator():
        full_response = ""

        # 1. Send products first
        yield f"data: {json.dumps({'type': 'products', 'products': products[:3]})}\n\n"

        # 2. Stream AI tokens
        async for chunk in stream_ollama_response(messages, products):
            yield chunk
            if chunk.startswith("data: "):
                try:
                    data = json.loads(chunk[6:])
                    if data.get("token"):
                        full_response += data["token"]
                except Exception:
                    pass

        # 3. Persist assistant response
        if full_response:
            redis_client.rpush(key, f"assistant:{full_response}")
            redis_client.expire(key, 86400)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/human-request")
async def human_request(request: Request, body: HumanRequest):
    ip = get_client_ip(request)
    if not rate_limit(ip, limit=2, window=300):
        raise HTTPException(429, "Too many human requests.")

    from datetime import datetime
    now = datetime.now()
    is_work = 1 <= now.weekday() <= 5 and 9 <= now.hour < 17
    return {
        "response": (
            "Thank you! A real assistant will contact you shortly."
            if is_work else
            "We're closed (Mon-Fri 9-17). We'll reply next business day."
        )
    }