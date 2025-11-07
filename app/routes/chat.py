# app/routes/chat.py
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import json
import redis
import os
import asyncio

from ..services.session import (
    get_session, create_session_id, sign_session,
    get_client_ip, rate_limit, r as redis_client,
    publish_message
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
# Helper: Stream Ollama → SSE + collect full text
# ------------------------------------------------------------------ #
async def ollama_stream_to_sse(messages: List[Dict], products: List[Dict]):
    full_response = ""
    try:
        async for chunk in stream_ollama_response(messages, products):
            yield chunk
            if chunk.startswith("data: "):
                try:
                    data = json.loads(chunk[6:])
                    if data.get("token"):
                        full_response += data["token"]
                except Exception:
                    pass
    except Exception as e:
        print(f"Ollama error: {e}")
        yield f"data: {json.dumps({'token': 'Sorry, service error.', 'done': True, 'error': True})}\n\n"
    finally:
        yield f"data: {json.dumps({'token': '', 'done': True})}\n\n"

    # DO NOT RETURN ANYTHING FROM ASYNC GENERATOR
    # full_response is captured in closure above


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

    # Publish immediately for admin panel
    publish_message(session_id, "user", body.message)

    # ------------------------------------------------------------------ #
    # Streaming generator: Products + AI + Admin messages (live)
    # ------------------------------------------------------------------ #
    async def event_generator():
        full_response = ""

        # 1. Send products
        yield f"data: {json.dumps({'type': 'products', 'products': products[:3]})}\n\n"

        # 2. Set up Redis pub/sub for admin messages
        pubsub = redis_client.pubsub()
        channel = f"session:{session_id}"
        pubsub.subscribe(channel)

        # 3. Start consuming Ollama stream directly
        try:
            # Open Ollama async generator
            ollama_gen = ollama_stream_to_sse(messages, products)
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

        # 4. Persist assistant response
        if full_response.strip():
            redis_client.rpush(key, f"assistant:{full_response}")
            redis_client.expire(key, 86400)
            publish_message(session_id, "assistant", full_response)

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