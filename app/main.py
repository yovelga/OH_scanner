"""
OHPR Media Monitor Bot — FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routes import telegram as telegram_router
from app.utils.logging_utils import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup / shutdown lifecycle."""
    settings = get_settings()

    # Configure logging before anything else
    setup_logging(level=settings.log_level, name="ohpr_bot")
    logger = logging.getLogger("ohpr_bot")

    # Ensure the temp directory exists at startup
    Path(settings.temp_dir).mkdir(parents=True, exist_ok=True)

    token_preview = settings.telegram_bot_token[:8] + "..." if settings.telegram_bot_token else "NOT SET"
    authorized = settings.authorized_user_ids_set or "NONE (all blocked)"
    logger.info(f"OHPR Bot starting up")
    logger.info(f"Bot token: {token_preview}")
    logger.info(f"Authorized users: {authorized}")
    logger.info(f"Temp dir: {settings.temp_dir}")

    yield

    logger.info("OHPR Bot shutting down.")


app = FastAPI(
    title="OHPR Media Monitor Bot",
    description=(
        "Telegram webhook service for media monitoring. "
        "Accepts URLs and PDF files, returns structured summaries."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(telegram_router.router)


# ── Utility endpoints ─────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health_check() -> JSONResponse:
    """Health check — returns 200 OK when the service is up."""
    return JSONResponse({"status": "ok", "service": "ohpr-bot"})


@app.get("/", tags=["Health"])
async def root() -> JSONResponse:
    """Root endpoint — confirms the service is running."""
    return JSONResponse(
        {
            "service": "OHPR Media Monitor Bot",
            "status": "running",
            "docs": "/docs",
            "health": "/health",
        }
    )
