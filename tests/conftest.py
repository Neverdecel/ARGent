"""Pytest fixtures for ARGent tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from argent.main import app


@pytest.fixture
async def client():
    """Async HTTP client for testing FastAPI endpoints."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
