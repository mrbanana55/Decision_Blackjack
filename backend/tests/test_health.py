"""Unit test for health check endpoint."""

from unittest.mock import AsyncMock, patch
import pytest
from httpx import ASGITransport, AsyncClient
from app.integrations.laya.schemas import LayaHealthStatus
from app.main import app
from app.simulation.interfaces import AgentFaultError


@pytest.mark.asyncio
async def test_health_check():
    """Verify that /health responds with 200 and healthy status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "backend"


@pytest.mark.asyncio
async def test_health_laya_success():
    """Verify that /health/laya returns status ok and details when Laya is reachable."""
    mock_health = LayaHealthStatus(
        status="ok",
        loaded=["typed-decisions"],
        device="mps",
    )
    with patch("app.api.health.LayaClient") as mock_client_cls:
        instance = mock_client_cls.return_value
        instance.check_health = AsyncMock(return_value=mock_health)
        instance.close = AsyncMock()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health/laya")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["laya"]["device"] == "mps"
            assert data["laya"]["loaded"] == ["typed-decisions"]


@pytest.mark.asyncio
async def test_health_laya_unavailable():
    """Verify that /health/laya reports unavailable status when Laya is disconnected."""
    with patch("app.api.health.LayaClient") as mock_client_cls:
        instance = mock_client_cls.return_value
        instance.check_health = AsyncMock(side_effect=AgentFaultError("Connection refused"))
        instance.close = AsyncMock()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health/laya")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unavailable"
            assert "Connection refused" in data["error"]
