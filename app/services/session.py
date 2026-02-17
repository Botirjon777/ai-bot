# app/services/session.py
import json
import secrets
import hmac
import hashlib
from fastapi import Request, Depends, HTTPException
from datetime import datetime
from threading import Lock
from collections import defaultdict
from time import time
from typing import List

from ..config import get_config
from ..utils.logging import get_logger

# ------------------------------------------------------------------ #
# Config
# ------------------------------------------------------------------ #
config = get_config()
logger = get_logger(__name__)

SESSION_SECRET = config.security.session_secret.encode()

logger.info("Using in-memory storage (Redis disabled)")

# ------------------------------------------------------------------ #
# In-Memory Storage
# ------------------------------------------------------------------ #
_sessions = defaultdict(list)  # session_id -> list of messages
_rate_limits = {}  # ip -> (count, expiry_time)
_lock = Lock()

def _cleanup_expired_rate_limits():
    """Remove expired rate limit entries"""
    now = time()
    with _lock:
        expired = [ip for ip, (_, expiry) in _rate_limits.items() if now >= expiry]
        for ip in expired:
            del _rate_limits[ip]

# ------------------------------------------------------------------ #
# Session Storage Functions
# ------------------------------------------------------------------ #
def get_session_history(session_id: str) -> List[str]:
    """Get chat history for a session"""
    with _lock:
        return _sessions.get(session_id, []).copy()

def add_to_session(session_id: str, message: str):
    """Add a message to session history"""
    with _lock:
        _sessions[session_id].append(message)
        # Limit to last 100 messages per session
        if len(_sessions[session_id]) > 100:
            _sessions[session_id] = _sessions[session_id][-100:]

def clear_session(session_id: str):
    """Clear session history"""
    with _lock:
        if session_id in _sessions:
            del _sessions[session_id]

# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #
def get_client_ip(request: Request) -> str:
    return request.headers.get("x-forwarded-for", request.client.host.split(",")[0])


def rate_limit(ip: str, limit: int = 5, window: int = 60) -> bool:
    """Check if IP is within rate limit"""
    _cleanup_expired_rate_limits()
    now = time()
    with _lock:
        if ip in _rate_limits:
            count, expiry = _rate_limits[ip]
            if now < expiry:
                if count >= limit:
                    return False
                _rate_limits[ip] = (count + 1, expiry)
            else:
                _rate_limits[ip] = (1, now + window)
        else:
            _rate_limits[ip] = (1, now + window)
        return True


def create_session_id() -> str:
    return secrets.token_urlsafe(32)


def sign_session(session_id: str) -> str:
    return hmac.new(SESSION_SECRET, session_id.encode(), hashlib.sha256).hexdigest()


def verify_session(session_id: str, signature: str) -> bool:
    return hmac.compare_digest(sign_session(session_id), signature)


# ------------------------------------------------------------------ #
# Publish message (no-op without Redis)
# ------------------------------------------------------------------ #
def publish_message(session_id: str, role: str, content: str):
    """Publish message (disabled - no Redis)"""
    pass  # No-op without Redis


# ------------------------------------------------------------------ #
# Dependency
# ------------------------------------------------------------------ #
async def get_session(request: Request):
    sid = request.cookies.get("session_id")
    sig = request.cookies.get("session_sig")
    if not sid or not sig or not verify_session(sid, sig):
        raise HTTPException(401, "Invalid session")
    return sid