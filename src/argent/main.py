"""FastAPI application entry point."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from argent.api.health import router as health_router
from argent.api.onboarding import router as onboarding_router
from argent.api.pages import router as pages_router
from argent.api.webhooks import router as webhooks_router
from argent.config import get_settings

settings = get_settings()

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

# Include routers
app.include_router(health_router)
app.include_router(webhooks_router)
app.include_router(onboarding_router)
app.include_router(pages_router)  # Pages router last (handles /)
