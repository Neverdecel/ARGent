"""FastAPI application entry point."""

from fastapi import FastAPI

from argent.api.health import router as health_router
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

# Include routers
app.include_router(health_router)
app.include_router(webhooks_router)


@app.get("/")
async def root() -> dict:
    """Root endpoint - landing page placeholder."""
    return {
        "name": settings.app_name,
        "message": "Welcome to ARGent - The game begins with a misdirected email...",
        "docs": "/docs" if settings.debug else None,
    }
