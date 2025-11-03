from fastapi import APIRouter, Request
from datetime import datetime
import requests
import os
import redis

from ..services.session import r as redis_client

router = APIRouter()

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3:3.8b")

# ------------------------------------------------------------------ #
@router.get("/faq")
async def faq():
    return {
        "faqs": [
            {"question": "What cable lengths do you offer?",
             "answer": "0.5m to 5m depending on the type."},
            {"question": "Do you make custom cables?",
             "answer": "Yes, with your preferred colors and connectors."},
            {"question": "What's your return policy?",
             "answer": "30-day returns for unused products."},
            {"question": "Do you ship internationally?",
             "answer": "Yes, we ship worldwide with tracking."},
            {"question": "Do you sell GPUs?",
             "answer": "No, we only sell cables and accessories."},
        ]
    }


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    key = f"session:{session_id}"
    redis_client.delete(key)
    return {"message": "Session cleared"}


@router.get("/health")
async def health():
    try:
        resp = requests.get(f"{OLLAMA_API_URL}/api/tags", timeout=2)
        ollama_status = "connected" if resp.status_code == 200 else "disconnected"
    except Exception:
        ollama_status = "disconnected"

    return {
        "status": "ok",
        "ollama": ollama_status,
        "model": OLLAMA_MODEL,
        "timestamp": datetime.now().isoformat(),
    }