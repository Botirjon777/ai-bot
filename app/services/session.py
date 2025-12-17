# app/services/session.py
import json
import secrets
import hmac
import hashlib
from fastapi import Request, Depends, HTTPException
import redis
from datetime import datetime

from ..config import get_config
from ..utils.logging import get_logger

# ------------------------------------------------------------------ #
# Config
# ------------------------------------------------------------------ #
config = get_config()
logger = get_logger(__name__)

r = redis.from_url(config.redis.url)
SESSION_SECRET = config.security.session_secret.encode()

# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #
def get_client_ip(request: Request) -> str:
    return request.headers.get("x-forwarded-for", request.client.host.split(",")[0])


def rate_limit(ip: str, limit: int = 5, window: int = 60) -> bool:
    key = f"rl:{ip}"
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window)
    return pipe.execute()[0] <= limit


def create_session_id() -> str:
    return secrets.token_urlsafe(32)


def sign_session(session_id: str) -> str:
    return hmac.new(SESSION_SECRET, session_id.encode(), hashlib.sha256).hexdigest()


def verify_session(session_id: str, signature: str) -> bool:
    return hmac.compare_digest(sign_session(session_id), signature)


# ------------------------------------------------------------------ #
# NEW: Publish message to Redis Pub/Sub
# ------------------------------------------------------------------ #
def publish_message(session_id: str, role: str, content: str):
    channel = f"session:{session_id}"
    payload = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    }
    r.publish(channel, json.dumps(payload))


# ------------------------------------------------------------------ #
# Dependency
# ------------------------------------------------------------------ #
async def get_session(request: Request):
    sid = request.cookies.get("session_id")
    sig = request.cookies.get("session_sig")
    if not sid or not sig or not verify_session(sid, sig):
        raise HTTPException(401, "Invalid session")
    return sid