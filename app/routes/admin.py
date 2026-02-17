# app/routes/admin.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import List, Dict
import json

from ..services.session import get_client_ip, rate_limit
from ..config import get_config
from ..utils.logging import get_logger

# ------------------------------------------------------------------ #
# Config
# ------------------------------------------------------------------ #
config = get_config()
logger = get_logger(__name__)

router = APIRouter()

# ------------------------------------------------------------------ #
# Admin Auth
# ------------------------------------------------------------------ #
ADMIN_API_KEY = config.security.admin_api_key

def verify_admin(request: Request):
    api_key = request.headers.get("x-admin-key")
    if api_key != ADMIN_API_KEY:
        raise HTTPException(403, "Invalid admin key")
    return True

# ------------------------------------------------------------------ #
# Admin endpoints (DISABLED without Redis)
# ------------------------------------------------------------------ #
@router.get("/admin/sessions")
async def list_sessions(_: bool = Depends(verify_admin)):
    """List all active sessions (disabled - Redis not in use)"""
    return {
        "sessions": [],
        "message": "Admin features disabled: Application uses in-memory storage (no Redis)"
    }


@router.get("/admin/session/{session_id}")
async def get_session_history(session_id: str, _: bool = Depends(verify_admin)):
    """Get full chat history of a session (disabled - Redis not in use)"""
    raise HTTPException(503, "Admin features disabled: Application uses in-memory storage (no Redis)")


@router.get("/admin/session/{session_id}/stream")
async def admin_stream_session(request: Request, session_id: str, _: bool = Depends(verify_admin)):
    """Real-time session monitoring (disabled - Redis not in use)"""
    raise HTTPException(503, "Admin streaming disabled: Application uses in-memory storage (no Redis)")


@router.post("/admin/session/{session_id}/send")
async def admin_send_message(
    session_id: str,
    body: Dict,
    _: bool = Depends(verify_admin)
):
    """Admin sends message to user (disabled - Redis not in use)"""
    raise HTTPException(503, "Admin messaging disabled: Application uses in-memory storage (no Redis)")