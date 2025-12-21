"""Tests for health check endpoints."""

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """Test basic health check returns healthy status."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_root_endpoint(client):
    """Test root endpoint returns landing page."""
    response = await client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "ARGent" in response.text
    assert "Enter" in response.text  # The CTA button
