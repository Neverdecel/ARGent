"""Health check endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from argent.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Basic health check endpoint."""
    return {"status": "healthy"}


@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)) -> dict:
    """Readiness check that verifies database connectivity."""
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"

    return {
        "status": "ready" if db_status == "connected" else "not_ready",
        "database": db_status,
    }
