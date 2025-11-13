# app/routes/chat.py (UPDATED)
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import json
import asyncio

from ..services.session import (
    get_session, create_session_id, sign_session,
    get_client_ip, rate_limit, r as redis_client,
    publish_message
)
from ..services.enhanced_search import smart_search, ProductFeedback
from ..services.enhanced_ollama import (
    stream_enhanced_ollama_response,
    IntentAnalyzer,
    LearningSystem
)
from ..services.search import contains_gpu
import os

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

class ProductClickRequest(BaseModel):
    product_id: str
    query: str

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
    # Streaming with Enhanced AI
    # ------------------------------------------------------------------ #
    async def event_generator():
        full_response = ""

        # 1. Send products with promotion flags
        products_to_send = []
        for p in products[:5]:
            product_data = {
                "id": p["id"],
                "title": p["title"],
                "price": p["price"],
                "vendor": p["vendor"]
            }
            if "promotion" in p:
                product_data["promotion"] = p["promotion"]
                product_data["discounted_price"] = p["discounted_price"]
            products_to_send.append(product_data)
        
        yield f"data: {json.dumps({'type': 'products', 'products': products_to_send})}\n\n"

        # 2. Send promotions banner if available
        if search_results["has_promotions"]:
            yield f"data: {json.dumps({'type': 'promotions', 'message': '🔥 Special deals available!'})}\n\n"

        # 3. Set up Redis pub/sub for admin messages
        pubsub = redis_client.pubsub()
        channel = f"session:{session_id}"
        pubsub.subscribe(channel)

        # 4. Stream enhanced AI response
        try:
            ollama_gen = stream_enhanced_ollama_response(messages, products, session_id)
            ollama_iter = ollama_gen.__aiter__()

            while True:
                # Check for admin messages
                msg = pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
                if msg and msg["type"] == "message":
                    try:
                        data = json.loads(msg["data"])
                        if data.get("role") == "admin":
                            yield f"data: {json.dumps({'type': 'admin_message', 'content': data['content']})}\n\n"
                    except Exception as e:
                        print(f"PubSub error: {e}")

                # Get next Ollama chunk
                try:
                    chunk = await asyncio.wait_for(ollama_iter.__anext__(), timeout=0.1)
                    yield chunk
                    if chunk.startswith("data: "):
                        try:
                            data = json.loads(chunk[6:])
                            if data.get("token"):
                                full_response += data["token"]
                        except:
                            pass
                except StopAsyncIteration:
                    break
                except asyncio.TimeoutError:
                    pass
                except Exception as e:
                    print(f"Ollama chunk error: {e}")
                    break

                await asyncio.sleep(0.05)

        except Exception as e:
            print(f"Stream error: {e}")
            yield f"data: {json.dumps({'token': 'Stream error.', 'done': True, 'error': True})}\n\n"
        finally:
            pubsub.unsubscribe(channel)
            try:
                await ollama_gen.aclose()
            except:
                pass

        # 5. Persist assistant response and log for learning
        if full_response.strip():
            redis_client.rpush(key, f"assistant:{full_response}")
            redis_client.expire(key, 86400)
            publish_message(session_id, "assistant", full_response)
            
            # Log search pattern for learning
            LearningSystem.log_search_pattern(session_id, body.message, specs)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
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