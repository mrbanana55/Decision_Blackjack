"""Async HTTP client for communicating with the local Laya inference engine."""

import logging
import time
from types import TracebackType
from typing import Any, Self

import httpx

from app.integrations.laya.config import LayaConfig
from app.integrations.laya.schemas import (
    ChoiceAnswer,
    LayaHealthStatus,
    SystemOneRequest,
    SystemOneResponse,
)
from app.simulation.interfaces import AgentFaultError

logger = logging.getLogger(__name__)


class LayaClient:
    """Async HTTP client for local Laya System One inference."""

    def __init__(
        self,
        config: LayaConfig | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config or LayaConfig()
        self._external_client = client
        self._client: httpx.AsyncClient | None = client

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            timeout = httpx.Timeout(
                timeout=self.config.timeout_seconds,
                connect=self.config.connect_timeout_seconds,
            )
            self._client = httpx.AsyncClient(timeout=timeout)
        return self._client

    async def __aenter__(self) -> Self:
        await self._get_client()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client if internally managed."""
        if self._client is not None and self._client != self._external_client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def check_health(self) -> LayaHealthStatus:
        """Probe GET /health on the target Laya server."""
        base_url = self.config.get_effective_url()
        url = f"{base_url}/health"
        client = await self._get_client()

        try:
            response = await client.get(url)
            if response.status_code != 200:
                raise AgentFaultError(
                    f"Laya health check failed with HTTP {response.status_code}: {response.text}"
                )
            data = response.json()
            return LayaHealthStatus.model_validate(data)
        except httpx.TimeoutException as exc:
            raise AgentFaultError(
                f"Laya health check timed out after {self.config.connect_timeout_seconds}s at {url}"
            ) from exc
        except httpx.ConnectError as exc:
            raise AgentFaultError(
                f"Laya service unreachable at {url}. Ensure Laya is running on the host machine."
            ) from exc
        except httpx.HTTPError as exc:
            raise AgentFaultError(f"Laya health check HTTP error: {exc}") from exc
        except Exception as exc:
            if isinstance(exc, AgentFaultError):
                raise
            raise AgentFaultError(f"Unexpected error during Laya health check: {exc}") from exc

    async def send_systemone(self, request: SystemOneRequest) -> SystemOneResponse:
        """Post a SystemOneRequest to POST /v1/systemone and parse the response."""
        base_url = self.config.get_effective_url()
        url = f"{base_url}/v1/systemone"
        client = await self._get_client()

        t0 = time.perf_counter()
        try:
            payload = request.model_dump()
            response = await client.post(url, json=payload)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            if response.status_code != 200:
                raise AgentFaultError(
                    f"Laya inference failed with HTTP {response.status_code}: {response.text}"
                )

            data = response.json()
            return self._parse_systemone_response(data, elapsed_ms)

        except httpx.TimeoutException as exc:
            raise AgentFaultError(
                f"Laya inference timed out after {self.config.timeout_seconds}s at {url}"
            ) from exc
        except httpx.ConnectError as exc:
            raise AgentFaultError(
                f"Laya service unreachable at {url}. Ensure Laya is running on the host machine."
            ) from exc
        except httpx.HTTPError as exc:
            raise AgentFaultError(f"Laya inference HTTP error: {exc}") from exc
        except Exception as exc:
            if isinstance(exc, AgentFaultError):
                raise
            raise AgentFaultError(f"Unexpected error during Laya inference: {exc}") from exc

    def _parse_systemone_response(self, data: dict[str, Any], elapsed_ms: float) -> SystemOneResponse:
        """Parse raw response JSON from TypeSafe System One API."""
        answers: dict[str, ChoiceAnswer] = {}
        meta: dict[str, Any] = data.get("meta", {})
        meta["latency_ms"] = elapsed_ms

        raw_answers = data.get("answers", {})
        # If answers is keyed by question ID
        if isinstance(raw_answers, dict):
            for q_id, q_ans in raw_answers.items():
                if isinstance(q_ans, dict):
                    choice = str(q_ans.get("choice") or q_ans.get("selected") or q_ans.get("value") or "")
                    confidence = float(q_ans.get("confidence", 1.0))
                    distribution = {str(k): float(v) for k, v in q_ans.get("distribution", {}).items()}
                    answers[q_id] = ChoiceAnswer(
                        choice=choice,
                        confidence=confidence,
                        distribution=distribution,
                    )
                elif isinstance(q_ans, str):
                    answers[q_id] = ChoiceAnswer(choice=q_ans, confidence=1.0)

        # Fallback: if top-level dict contains question keys directly
        if not answers:
            for k, v in data.items():
                if k not in ("meta", "detail", "status") and isinstance(v, dict) and "choice" in v:
                    answers[k] = ChoiceAnswer.model_validate(v)

        return SystemOneResponse(answers=answers, meta=meta)
