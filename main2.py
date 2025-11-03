# main.py
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
from opensearchpy import OpenSearch
import os
import redis
import hashlib
import hmac
import secrets
import time
import requests
import json
from datetime import datetime

# -----------------------------
# App & CORS
# -----------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Config
# -----------------------------
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3:3.8b")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
SESSION_SECRET = os.getenv("SESSION_SECRET", "change-me-to-32-bytes-secret-key-here").encode()

opensearch_client = OpenSearch(
    hosts=[{"host": "localhost", "port": 9200}],
    http_auth=("admin", "Str0ngP@ssw0rd1245!"),
    use_ssl=True,
    verify_certs=False,
    ssl_show_warn=False,
)
r = redis.from_url(REDIS_URL)

# -----------------------------
# Security Helpers
# -----------------------------
def get_client_ip(request: Request) -> str:
    return request.headers.get("x-forwarded-for", request.client.host.split(",")[0])

def is_nonsense(text: str) -> bool:
    words = text.lower().split()
    if len(words) < 2: return True
    if len(set(words)) / len(words) < 0.3: return True
    return False

def rate_limit(ip: str, limit: int = 5, window: int = 60) -> bool:
    key = f"rl:{ip}"
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window)
    count = pipe.execute()[0]
    return count <= limit

def create_session_id() -> str:
    return secrets.token_urlsafe(32)

def sign_session(session_id: str) -> str:
    return hmac.new(SESSION_SECRET, session_id.encode(), hashlib.sha256).hexdigest()

def verify_session(session_id: str, signature: str) -> bool:
    return hmac.compare_digest(sign_session(session_id), signature)

# -----------------------------
# Session Dependency
# -----------------------------
async def get_session(request: Request):
    session_id = request.cookies.get("session_id")
    signature = request.cookies.get("session_sig")
    if not session_id or not signature or not verify_session(session_id, signature):
        raise HTTPException(401, "Invalid session")
    return session_id

# -----------------------------
# Models
# -----------------------------
class ChatRequest(BaseModel):
    message: str
    user_info: Optional[dict] = None

class HumanRequest(BaseModel):
    name: str
    email: str

# -----------------------------
# GPU Blocking
# -----------------------------
GPU_KEYWORDS = {"gpu", "rtx", "gtx", "radeon", "nvidia", "amd", "4090", "4080", "3080", "rx", "graphics card", "video card"}
def contains_gpu(text: str) -> bool:
    return any(kw in text.lower() for kw in GPU_KEYWORDS)

# -----------------------------
# Product Search
# -----------------------------
def search_products(query: str, limit: int = 5) -> List[dict]:
    if contains_gpu(query): 
        return []
    try:
        resp = opensearch_client.search(
            index="products-index",
            body={
                "query": {
                    "bool": {
                        "should": [
                            {"match": {"title": {"query": query, "boost": 2}}},
                            {"match": {"vendor": {"query": query}}},
                        ],
                        "must": [{"term": {"sellable": True}}]
                    }
                },
                "size": limit * 3
            }
        )
        hits = resp["hits"]["hits"]
        products = []
        for hit in hits:
            src = hit["_source"]
            title = src.get("title", "")
            vendor = src.get("vendor", "")
            if not contains_gpu(f"{title} {vendor}"):
                products.append({
                    "id": src.get("id"),
                    "title": title,
                    "price": src.get("price"),
                    "vendor": vendor,
                    "sellable": src.get("sellable")
                })
        return products[:limit]
    except Exception as e:
        print(f"OpenSearch error: {e}")
        return []

# -----------------------------
# Ollama AI Response (Streaming)
# -----------------------------
def build_prompt(messages: List[dict], products: List[dict]) -> str:
    """Build the prompt for Ollama"""
    system_prompt = """You are a helpful AI assistant for a cable and PC accessories e-commerce store.
Your role is to help customers find the right cables, custom cables, and cable-related products.

IMPORTANT RULES:
1. ONLY discuss products related to cables (PC cables, custom cables, USB cables, HDMI cables, power cables, adapters, etc.)
2. If users ask about products NOT related to cables (like GPUs, graphics cards, games, consoles, furniture, clothing), politely inform them: "I apologize, but we only sell cables and cable-related accessories. We don't carry that item."
3. ALWAYS check product availability before recommending
4. If a product is out of stock, mention it clearly and suggest alternatives
5. Be concise and helpful (2-3 sentences maximum)
6. Remember the conversation context
7. Ask clarifying questions if needed (cable type, length, connector type, etc.)

PRODUCT KNOWLEDGE:
- We sell: PC cables, custom cables, USB cables, HDMI cables, power cables (24-pin, 8-pin, etc.), DisplayPort cables, Ethernet cables, adapters, cable extensions, cable sleeves, and cable management accessories
- We DO NOT sell: Gaming consoles, games, computers, monitors, keyboards, mice, GPUs, graphics cards, or any non-cable products"""

    if products:
        system_prompt += "\n\nCURRENT AVAILABLE PRODUCTS:\n"
        for p in products:
            system_prompt += f"- {p['title']} (${p['price']}) by {p['vendor']}\n"

    # Build conversation context
    conversation = system_prompt + "\n\n"
    for msg in messages[-10:]:  # Last 10 messages for context
        role = "User" if msg["role"] == "user" else "Assistant"
        conversation += f"{role}: {msg['content']}\n"
    
    conversation += "Assistant:"
    return conversation

async def stream_ollama_response(messages: List[dict], products: List[dict]):
    """Stream Ollama response token by token"""
    try:
        prompt = build_prompt(messages, products)
        
        # Call Ollama API with streaming enabled
        response = requests.post(
            f"{OLLAMA_API_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "top_k": 40,
                    "num_predict": 200,
                }
            },
            stream=True,
            timeout=60
        )
        
        if response.status_code == 200:
            # Stream the response
            for line in response.iter_lines():
                if line:
                    try:
                        json_response = json.loads(line)
                        token = json_response.get("response", "")
                        done = json_response.get("done", False)
                        
                        if token:
                            yield f"data: {json.dumps({'token': token, 'done': False})}\n\n"
                        
                        if done:
                            yield f"data: {json.dumps({'token': '', 'done': True})}\n\n"
                            break
                    except json.JSONDecodeError:
                        continue
        else:
            error_msg = "Sorry, I'm having trouble processing your request right now."
            yield f"data: {json.dumps({'token': error_msg, 'done': True, 'error': True})}\n\n"
            
    except requests.exceptions.Timeout:
        error_msg = "Sorry, the response is taking too long. Please try again."
        yield f"data: {json.dumps({'token': error_msg, 'done': True, 'error': True})}\n\n"
    except requests.exceptions.ConnectionError:
        error_msg = "Sorry, I'm currently unavailable. Please try again in a moment."
        yield f"data: {json.dumps({'token': error_msg, 'done': True, 'error': True})}\n\n"
    except Exception as e:
        print(f"Ollama error: {e}")
        error_msg = "Sorry, I'm having trouble right now."
        yield f"data: {json.dumps({'token': error_msg, 'done': True, 'error': True})}\n\n"

# -----------------------------
# Endpoints
# -----------------------------
@app.get("/api/session")
async def init_session(response: JSONResponse):
    session_id = create_session_id()
    signature = sign_session(session_id)

    # FOR DEV: Use lax + no secure
    # FOR PROD: Use None + secure=True
    is_dev = os.getenv("ENV", "dev") == "dev"
    secure = not is_dev
    samesite = "lax" if is_dev else "none"

    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path="/",
    )
    response.set_cookie(
        key="session_sig",
        value=signature,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path="/",
    )
    return {"session_id": session_id}

@app.post("/api/chat")
async def chat(request: Request, body: ChatRequest, session_id: str = Depends(get_session)):
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

    # Search for products first (fast)
    products = search_products(body.message)
    
    # Get conversation history from Redis
    key = f"session:{session_id}"
    history = r.lrange(key, 0, -1)
    messages = []
    for item in history:
        item_str = item.decode('utf-8')
        if ':' in item_str:
            role, content = item_str.split(':', 1)
            messages.append({"role": role, "content": content})
    
    # Add current user message
    user_msg = {"role": "user", "content": body.message}
    messages.append(user_msg)
    
    # Store user message immediately
    r.rpush(key, f"{user_msg['role']}:{user_msg['content']}")
    r.expire(key, 86400)

    # Create streaming response
    async def event_generator():
        full_response = ""
        
        # First, send products immediately
        yield f"data: {json.dumps({'type': 'products', 'products': products[:3]})}\n\n"
        
        # Then stream the AI response
        async for chunk in stream_ollama_response(messages, products):
            yield chunk
            
            # Extract token from chunk to build full response
            if chunk.startswith("data: "):
                try:
                    data = json.loads(chunk[6:])
                    if data.get('token'):
                        full_response += data['token']
                except:
                    pass
        
        # Store the complete AI response in Redis
        if full_response:
            r.rpush(key, f"assistant:{full_response}")
            r.expire(key, 86400)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/api/human-request")
async def human_request(request: Request, body: HumanRequest):
    ip = get_client_ip(request)
    if not rate_limit(ip, limit=2, window=300):
        raise HTTPException(429, "Too many human requests.")

    now = datetime.now()
    is_work = 1 <= now.weekday() <= 5 and 9 <= now.hour < 17
    return {
        "response": "Thank you! A real assistant will contact you shortly."
        if is_work else
        "We're closed (Mon-Fri 9-17). We'll reply next business day."
    }

@app.get("/api/faq")
async def faq():
    return {
        "faqs": [
            {"question": "What cable lengths do you offer?", "answer": "0.5m to 5m depending on the type."},
            {"question": "Do you make custom cables?", "answer": "Yes, with your preferred colors and connectors."},
            {"question": "What's your return policy?", "answer": "30-day returns for unused products."},
            {"question": "Do you ship internationally?", "answer": "Yes, we ship worldwide with tracking."},
            {"question": "Do you sell GPUs?", "answer": "No, we only sell cables and accessories."},
        ]
    }

@app.delete("/api/session/{session_id}")
async def clear_session(session_id: str):
    """Clear chat session"""
    key = f"session:{session_id}"
    r.delete(key)
    return {"message": "Session cleared"}

@app.get("/api/health")
async def health():
    """Health check - also checks Ollama connection"""
    try:
        ollama_response = requests.get(f"{OLLAMA_API_URL}/api/tags", timeout=2)
        ollama_status = "connected" if ollama_response.status_code == 200 else "disconnected"
    except:
        ollama_status = "disconnected"
    
    return {
        "status": "ok",
        "ollama": ollama_status,
        "model": OLLAMA_MODEL,
        "timestamp": datetime.now().isoformat()
    }

@app.exception_handler(HTTPException)
async def http_error_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)