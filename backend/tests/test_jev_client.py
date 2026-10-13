"""Tests for JevClient HTTP communication, Bearer authentication, retry backoff, and fault translation."""

import json

import httpx
import pytest

from app.integrations.jev.client import JevClient
from app.integrations.jev.config import JevConfig
from app.integrations.jev.schemas import (
    ChoiceQuestion,
    JevHealthStatus,
    SystemOneRequest,
    SystemOneResponse,
)
from app.simulation.interfaces import AgentFaultError


@pytest.fixture
def mock_config() -> JevConfig:
    return JevConfig(
        api_key="test_api_key_valid",
        api_url="https://api.typesafe.ai/v1/systemone",
        model="jev-latest",
        timeout_seconds=1.0,
        connect_timeout_seconds=0.5,
        max_retries=2,
    )


@pytest.mark.asyncio
async def test_check_health_success(mock_config):
    """Verify check_health queries /health with Bearer auth and parses response."""
    mock_payload = {"status": "ok", "service": "typesafe-api"}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/health"
        assert request.headers.get("Authorization") == "Bearer test_api_key_valid"
        return httpx.Response(200, json=mock_payload, headers={"content-type": "application/json"})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = JevClient(config=mock_config, client=mock_client)
    health: JevHealthStatus = await client.check_health()

    assert health.status == "ok"
    assert health.provider == "typesafe"
    assert health.has_api_key is True
    assert health.model == "jev-latest"
    await client.close()


@pytest.mark.asyncio
async def test_check_health_missing_key():
    """Verify check_health returns unavailable status when API key is empty."""
    config = JevConfig(api_key="", api_url="https://api.typesafe.ai/v1/systemone")
    client = JevClient(config=config)
    health = await client.check_health()
    assert health.status == "unavailable"
    assert health.has_api_key is False
    assert "Missing TYPESAFE_API_KEY" in health.details.get("error", "")
    await client.close()


@pytest.mark.asyncio
async def test_check_health_connect_error(mock_config):
    """Verify check_health translates connection errors to AgentFaultError."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Failed to connect", request=request)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = JevClient(config=mock_config, client=mock_client)
    with pytest.raises(AgentFaultError, match="TypeSafe service unreachable"):
        await client.check_health()
    await client.close()


@pytest.mark.asyncio
async def test_check_health_timeout(mock_config):
    """Verify check_health translates timeout errors to AgentFaultError."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("Read timed out")

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = JevClient(config=mock_config, client=mock_client)
    with pytest.raises(AgentFaultError, match="timed out"):
        await client.check_health()
    await client.close()


@pytest.mark.asyncio
async def test_send_systemone_success(mock_config):
    """Verify send_systemone sends JSON payload with Bearer auth and parses response."""
    mock_response = {
        "model": "jev-1.13.0",
        "answers": {
            "action": {
                "choice": "hit",
                "confidence": 0.88,
                "probabilities": {"hit": 0.88, "stand": 0.12},
            }
        },
        "usage": {
            "input_tokens": 120,
            "output_tokens": 15,
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/systemone"
        assert request.headers.get("Authorization") == "Bearer test_api_key_valid"
        body = json.loads(request.content)
        assert body["model"] == "jev-latest"
        assert "questions" in body
        assert "action" in body["questions"]
        return httpx.Response(200, json=mock_response)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = JevClient(config=mock_config, client=mock_client)

    req = SystemOneRequest(
        state="Test state",
        model="jev-latest",
        questions={
            "action": ChoiceQuestion(
                instructions="Hit or stand?",
                criteria={"hit": "Draw card", "stand": "End turn"},
            )
        },
    )

    resp: SystemOneResponse = await client.send_systemone(req)
    assert resp.model == "jev-1.13.0"
    assert "action" in resp.answers
    ans = resp.answers["action"]
    assert ans.choice == "hit"
    assert ans.confidence == 0.88
    assert ans.probabilities["hit"] == 0.88
    assert ans.distribution["hit"] == 0.88
    assert resp.usage is not None
    assert resp.usage.input_tokens == 120
    assert resp.usage.output_tokens == 15
    assert resp.meta["latency_ms"] >= 0.0
    await client.close()


@pytest.mark.asyncio
async def test_send_systemone_auth_error(mock_config):
    """Verify HTTP 401 raises AgentFaultError immediately without useless retries."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="Invalid API key")

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = JevClient(config=mock_config, client=mock_client)

    req = SystemOneRequest(
        state="Test",
        questions={
            "action": ChoiceQuestion(
                instructions="Hit or stand?",
                criteria={"hit": "Hit", "stand": "Stand"},
            )
        },
    )

    with pytest.raises(AgentFaultError, match="HTTP 401"):
        await client.send_systemone(req)
    await client.close()


@pytest.mark.asyncio
async def test_send_systemone_auth_error_403(mock_config):
    """Verify HTTP 403 raises AgentFaultError immediately without useless retries."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text='{"detail":{"error_type":"authentication_error","message":"Must supply an API key!"}}')

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = JevClient(config=mock_config, client=mock_client)

    req = SystemOneRequest(
        state="Test",
        questions={
            "action": ChoiceQuestion(
                instructions="Hit or stand?",
                criteria={"hit": "Hit", "stand": "Stand"},
            )
        },
    )

    with pytest.raises(AgentFaultError, match="HTTP 403"):
        await client.send_systemone(req)
    await client.close()


@pytest.mark.asyncio
async def test_send_systemone_missing_api_key():
    """Verify missing API key raises AgentFaultError before dispatching network request."""
    config = JevConfig(api_key="", api_url="https://api.typesafe.ai/v1/systemone")
    client = JevClient(config=config)

    req = SystemOneRequest(
        state="Test",
        questions={
            "action": ChoiceQuestion(
                instructions="Hit or stand?",
                criteria={"hit": "Hit", "stand": "Stand"},
            )
        },
    )

    with pytest.raises(AgentFaultError, match="Missing TYPESAFE_API_KEY"):
        await client.send_systemone(req)
    await client.close()


@pytest.mark.asyncio
async def test_send_systemone_retry_on_429_success(mock_config):
    """Verify HTTP 429 triggers retry and succeeds on subsequent attempt."""
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "0.01"}, text="Rate limit exceeded")
        return httpx.Response(
            200,
            json={
                "model": "jev-latest",
                "answers": {"action": {"choice": "stand", "confidence": 0.95}},
            },
        )

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = JevClient(config=mock_config, client=mock_client)

    req = SystemOneRequest(
        state="Test",
        questions={
            "action": ChoiceQuestion(
                instructions="Hit or stand?",
                criteria={"hit": "Hit", "stand": "Stand"},
            )
        },
    )

    resp = await client.send_systemone(req)
    assert attempts == 2
    assert resp.answers["action"].choice == "stand"
    await client.close()


@pytest.mark.asyncio
async def test_send_systemone_retry_exhausted(mock_config):
    """Verify HTTP 429 raises AgentFaultError when retries are exhausted."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "0.01"}, text="Rate limit exceeded")

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = JevClient(config=mock_config, client=mock_client)

    req = SystemOneRequest(
        state="Test",
        questions={
            "action": ChoiceQuestion(
                instructions="Hit or stand?",
                criteria={"hit": "Hit", "stand": "Stand"},
            )
        },
    )

    with pytest.raises(AgentFaultError, match="exhausted after 3 attempts"):
        await client.send_systemone(req)
    await client.close()
