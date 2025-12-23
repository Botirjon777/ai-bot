from fastapi import APIRouter, Request
from datetime import datetime
import requests

from ..services.session import clear_session as clear_session_storage
from ..config import get_config
from ..knowledge import FAQSystem
from ..utils.logging import get_logger

# ------------------------------------------------------------------ #
# Config
# ------------------------------------------------------------------ #
config = get_config()
logger = get_logger(__name__)
faq_system = FAQSystem()

router = APIRouter()

# ------------------------------------------------------------------ #
@router.get("/faq")
async def faq():
    """Get all FAQs organized by category."""
    categories = faq_system.get_all_categories()
    
    # Get all FAQs
    all_faqs = []
    for category in categories:
        faqs = faq_system.get_by_category(category["name"])
        for faq_item in faqs:
            all_faqs.append({
                "category": category["name"],
                "question": faq_item["question"],
                "answer": faq_item["answer"]
            })
    
    return {"faqs": all_faqs, "categories": categories}


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    key = f"session:{session_id}"
    redis_client.delete(key)
    return {"message": "Session cleared"}


@router.get("/health")
async def health():
    """Comprehensive health check for all services."""
    # Check Ollama
    try:
        resp = requests.get(f"{config.ollama.api_url}/api/tags", timeout=2)
        ollama_status = "connected" if resp.status_code == 200 else "disconnected"
    except Exception as e:
        logger.warning(f"Ollama health check failed: {e}")
        ollama_status = "disconnected"
    
    # Redis is disabled
    redis_status = "disabled (not in use)"
    
    # Check OpenSearch
    try:
        from ..services.search import opensearch_client
        opensearch_client.cluster.health()
        opensearch_status = "connected"
    except Exception as e:
        logger.warning(f"OpenSearch health check failed: {e}")
        opensearch_status = "disconnected"

    return {
        "status": "ok",
        "ollama": ollama_status,
        "redis": redis_status,
        "opensearch": opensearch_status,
        "model": config.ollama.model,
        "environment": config.env,
        "timestamp": datetime.now().isoformat(),
    }