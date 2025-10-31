# main.py
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
from opensearchpy import OpenSearch
from openai import OpenAI
import os
import redis
import hashlib
import hmac
import secrets
import time
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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "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")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
SESSION_SECRET = os.getenv("SESSION_SECRET", "change-me-to-32-bytes").encode()

client = OpenAI(api_key=OPENAI_API_KEY)
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
GPU_KEYWORDS = {"gpu", "rtx", "gtx", "radeon", "nvidia", "amd", "4090", "4080", "3080", "rx"}
def contains_gpu(text: str) -> bool:
    return any(kw in text.lower() for kw in GPU_KEYWORDS)

# -----------------------------
# Product Search
# -----------------------------
def search_products(query: str, limit: int = 5) -> List[dict]:
    if contains_gpu(query): return []
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
        print(e)
        return []

# -----------------------------
# AI Response
# -----------------------------
def ai_respond(messages: List[dict], products: List[dict]) -> str:
    try:
        system = """You are a helpful cable assistant. ONLY talk about cables. NEVER mention GPUs."""
        if products:
            system += "\n\nAvailable:\n" + "\n".join([
                f"- {p['title']} (${p['price']}) by {p['vendor']}"
                for p in products
            ])
        full = [{"role": "system", "content": system}] + messages[-10:]
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=full,
            temperature=0.7,
            max_tokens=400
        )
        return resp.choices[0].message.content
    except Exception as e:
        return "Sorry, I'm having trouble right now."

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
            "response": "We only sell cables. We do **not** sell GPUs.",
            "session_id": session_id,
            "suggested_products": None
        })

    products = search_products(body.message)
    user_msg = {"role": "user", "content": body.message}
    assistant_msg = {"role": "assistant", "content": ai_respond([user_msg], products)}

    key = f"session:{session_id}"
    r.rpush(key, f"{user_msg['role']}:{user_msg['content']}")
    r.rpush(key, f"{assistant_msg['role']}:{assistant_msg['content']}")
    r.expire(key, 86400)

    return {
        "response": assistant_msg["content"],
        "session_id": session_id,
        "suggested_products": products[:3]
    }

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

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.exception_handler(HTTPException)
async def http_error_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})