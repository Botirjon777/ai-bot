from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

# ------------------------------------------------------------------ #
# CORS
# ------------------------------------------------------------------ #
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------ #
# Import routers after app creation (avoid circular imports)
# ------------------------------------------------------------------ #
from .routes import chat, system  # noqa: E402
app.include_router(chat.router, prefix="/api")
app.include_router(system.router, prefix="/api")