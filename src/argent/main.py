"""FastAPI application entry point."""

import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from argent.api.evidence import router as evidence_router
from argent.api.health import router as health_router
from argent.api.inbox import router as inbox_router
from argent.api.onboarding import router as onboarding_router
from argent.api.pages import router as pages_router
from argent.api.webhooks import router as webhooks_router
from argent.config import get_settings

settings = get_settings()

# Configure logging
log_level = logging.DEBUG if settings.debug else logging.INFO
logging.basicConfig(
    level=log_level,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
# Reduce noise from third-party libraries
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
logger.info("Starting ARGent with debug=%s, log_level=%s", settings.debug, log_level)

app = FastAPI(
    title=settings.app_name,
    description="An AI-driven alternate reality game",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Mount static files
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# Serve robots.txt at root (for search engine exclusion)
@app.get("/robots.txt", include_in_schema=False)
async def robots_txt() -> FileResponse:
    """Serve robots.txt to prevent indexing of secret pages."""
    return FileResponse(STATIC_DIR / "robots.txt", media_type="text/plain")


# Include routers
app.include_router(health_router)
app.include_router(webhooks_router)
app.include_router(onboarding_router)
app.include_router(inbox_router)
app.include_router(evidence_router)  # Evidence dashboard (/access/{key})
app.include_router(pages_router)  # Pages router last (handles /)
