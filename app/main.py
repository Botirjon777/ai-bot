from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_config
from .utils.logging import setup_logging, get_logger

# ------------------------------------------------------------------ #
# Setup
# ------------------------------------------------------------------ #
config = get_config()

# Setup logging
setup_logging(
    level="DEBUG" if config.debug else "INFO",
    log_file="logs/app.log" if not config.is_development else None
)

logger = get_logger(__name__)
logger.info(f"Starting AI Bot in {config.env} environment")

app = FastAPI(
    title="AI Cable Store Assistant",
    description="AI-powered chatbot for cable e-commerce",
    version="2.0.0",
    debug=config.debug
)

# ------------------------------------------------------------------ #
# CORS
# ------------------------------------------------------------------ #
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------ #
# Import routers after app creation (avoid circular imports)
# ------------------------------------------------------------------ #
from .routes import chat, system, admin  # noqa: E402
app.include_router(chat.router, prefix="/api")
app.include_router(system.router, prefix="/api")
app.include_router(admin.router, prefix="/api")