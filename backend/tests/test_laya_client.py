"""Tests for LayaClient HTTP communication, health probe, and fault translation."""

import json

import httpx
import pytest

from app.integrations.laya.client import LayaClient
from app.integrations.laya.config import LayaConfig
from app.integrations.laya.schemas import (
    ChoiceQuestion,
    LayaHealthStatus,
    SystemOneRequest,
    SystemOneResponse,
)
from app.simulation.interfaces import AgentFaultError


@pytest.fixture
def mock_config() -> LayaConfig:
    return LayaConfig(base_url="http://127.0.0.1:1234", timeout_seconds=1.0, connect_timeout_seconds=0.5)


@pytest.mark.asyncio
async def test_check_health_success(mock_config):
    """Verify check_health parses successful 200 OK response into LayaHealthStatus."""
    mock_payload = {
        "status": "ok",
        "loaded": ["english", "multilingual", "typed-decisions"],
        "revisions": {
            "english": "7b928d828b7b0e022f929d9bd2e44165aa270148",
            "typed-decisions": "7b928d828b7b0e022f929d9bd2e44165aa270148",
        },
        "device": "mps",
        "device_is_preference": False,
        "checkpoint_devices": {"typed-decisions": "mps"},
        "cpu_fallbacks": {},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/health"
        return httpx.Response(200, json=mock_payload)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = LayaClient(config=mock_config, client=mock_client)
    health: LayaHealthStatus = await client.check_health()

    assert health.status == "ok"
    assert health.device == "mps"
    assert "typed-decisions" in health.loaded
    assert health.revisions["typed-decisions"] == "7b928d828b7b0e022f929d9bd2e44165aa270148"
    await client.close()


@pytest.mark.asyncio
async def test_check_health_server_error(mock_config):
    """Verify check_health raises AgentFaultError on non-200 responses."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Model Error")

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = LayaClient(config=mock_config, client=mock_client)
    with pytest.raises(AgentFaultError, match="HTTP 500"):
        await client.check_health()
    await client.close()


@pytest.mark.asyncio
async def test_check_health_connect_error(mock_config):
    """Verify check_health translates connection errors to AgentFaultError."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Failed to connect", request=request)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = LayaClient(config=mock_config, client=mock_client)
    with pytest.raises(AgentFaultError, match="Laya service unreachable"):
        await client.check_health()
    await client.close()


@pytest.mark.asyncio
async def test_check_health_timeout(mock_config):
    """Verify check_health translates timeout errors to AgentFaultError."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("Read timed out")

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = LayaClient(config=mock_config, client=mock_client)
    with pytest.raises(AgentFaultError, match="timed out"):
        await client.check_health()
    await client.close()


@pytest.mark.asyncio
async def test_send_systemone_success(mock_config):
    """Verify send_systemone sends JSON payload and parses ChoiceAnswer response."""
    mock_response = {
        "answers": {
            "action": {
                "choice": "hit",
                "confidence": 0.95,
                "distribution": {"hit": 0.95, "stand": 0.05},
            }
        },
        "meta": {
            "model": "typed-decisions",
            "device": "mps",
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/systemone"
        data = json.loads(request.content.decode("utf-8"))
        assert "questions" in data
        return httpx.Response(200, json=mock_response)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    request = SystemOneRequest(
        state="Blackjack Hand State",
        questions={
            "action": ChoiceQuestion(
                instructions="Choose action",
                criteria={"hit": "Draw card", "stand": "Keep hand"},
            )
        },
    )

    async with LayaClient(config=mock_config, client=mock_client) as client:
        result: SystemOneResponse = await client.send_systemone(request)

        assert "action" in result.answers
        assert result.answers["action"].choice == "hit"
        assert result.answers["action"].confidence == 0.95
        assert result.meta["latency_ms"] >= 0.0
        assert result.meta["device"] == "mps"


@pytest.mark.asyncio
async def test_send_systemone_fault_propagation(mock_config):
    """Verify send_systemone raises AgentFaultError on network/HTTP faults."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": "Bad schema"})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    request = SystemOneRequest(
        state="Hand",
        questions={
            "action": ChoiceQuestion(
                instructions="Act",
                criteria={"hit": "Hit card", "stand": "Stand hand"},
            )
        },
    )

    async with LayaClient(config=mock_config, client=mock_client) as client:
        with pytest.raises(AgentFaultError, match="HTTP 422"):
            await client.send_systemone(request)
