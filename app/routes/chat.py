# app/routes/chat.py (UPDATED - Non-Streaming)
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Dict

from ..models.chat import ChatRequest, HumanRequest, ProductClickRequest
from ..services.session import (
    get_session, create_session_id, sign_session,
    get_client_ip, rate_limit, r as redis_client,
    publish_message
)
from ..services.enhanced_search import smart_search, ProductFeedback
from ..services.enhanced_ollama import (
    get_enhanced_ollama_response,
    IntentAnalyzer,
    LearningSystem
)
from ..services.search import contains_gpu
from ..config import get_config
from ..utils.logging import get_logger
from ..utils.validators import validate_message

# ------------------------------------------------------------------ #
# Config
# ------------------------------------------------------------------ #
config = get_config()
logger = get_logger(__name__)

router = APIRouter()

# ------------------------------------------------------------------ #
# Routes
# ------------------------------------------------------------------ #
@router.get("/session")
async def init_session(response: JSONResponse):
    sid = create_session_id()
    sig = sign_session(sid)

    is_dev = config.is_development
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

    # Validate message
    try:
        validate_message(body.message)
    except Exception as e:
        raise HTTPException(400, str(e))

    if contains_gpu(body.message):
        return JSONResponse({
            "response": "We only sell cables and cable-related accessories. We do **not** sell GPUs or graphics cards.",
            "session_id": session_id,
            "suggested_products": None
        })

    # Load conversation history
    key = f"session:{session_id}"
    history = redis_client.lrange(key, 0, -1)
    messages: List[Dict] = []
    for item in history:
        try:
            role, content = item.decode("utf-8").split(":", 1)
            messages.append({"role": role, "content": content})
        except:
            continue

    # Append user message
    user_msg = {"role": "user", "content": body.message}
    messages.append(user_msg)
    redis_client.rpush(key, f"{user_msg['role']}:{user_msg['content']}")
    redis_client.expire(key, 86400)

    # Publish for admin panel
    publish_message(session_id, "user", body.message)

    # ENHANCED: Extract specifications and perform smart search
    specs = IntentAnalyzer.extract_specifications(body.message)
    search_results = smart_search(body.message, specs, session_id)
    
    products = search_results["products"]
    promotions = search_results["promotions"]

    # ------------------------------------------------------------------ #
    # Non-Streaming Response (Complete Answer at Once)
    # ------------------------------------------------------------------ #
    try:
        # Get complete AI response
        ai_response = get_enhanced_ollama_response(messages, products, session_id)
        
        # Persist assistant response
        redis_client.rpush(key, f"assistant:{ai_response}")
        redis_client.expire(key, 86400)
        publish_message(session_id, "assistant", ai_response)
        
        # Log search pattern for learning
        LearningSystem.log_search_pattern(session_id, body.message, specs)
        
        # Prepare products for response
        products_to_send = []
        for p in products[:5]:
            product_data = {
                "id": p["id"],
                "title": p["title"],
                "price": p["price"],
                "vendor": p["vendor"],
                "slug": p.get("slug"),
                "sellable": p.get("sellable", True)
            }
            if "promotion" in p:
                product_data["promotion"] = p["promotion"]
                product_data["discounted_price"] = p["discounted_price"]
            products_to_send.append(product_data)
        
        # Return complete JSON response
        return JSONResponse({
            "response": ai_response,
            "session_id": session_id,
            "suggested_products": products_to_send if products_to_send else None,
            "has_promotions": search_results["has_promotions"]
        })
    
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return JSONResponse(
            {
                "response": "Sorry, I am having trouble right now. Please try again.",
                "session_id": session_id,
                "suggested_products": None,
                "has_promotions": False,
                "error": True
            },
            status_code=500
        )


@router.post("/product-click")
async def track_product_click(
    request: Request,
    body: ProductClickRequest,
    session_id: str = Depends(get_session)
):
    """Track when user clicks on a product for learning"""
    ProductFeedback.log_product_click(session_id, body.product_id, body.query)
    LearningSystem.log_search_pattern(session_id, body.query, {}, body.product_id)
    return {"status": "tracked"}


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