"""Async HTTP client for communicating with the TypeSafe Jev System One API."""

import asyncio
import logging
import time
from types import TracebackType
from typing import Any, Self

import httpx

from app.integrations.jev.config import JevConfig
from app.integrations.jev.schemas import (
    ChoiceAnswer,
    JevHealthStatus,
    SystemOneRequest,
    SystemOneResponse,
    UsageInfo,
)
from app.simulation.interfaces import AgentFaultError

logger = logging.getLogger(__name__)


class JevClient:
    """Async HTTP client for TypeSafe Jev System One inference with retry backoff."""

    def __init__(
        self,
        config: JevConfig | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config or JevConfig()
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

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.config.api_key:
            api_key = self.config.api_key.strip().strip("'\"")
            headers["Authorization"] = f"Bearer {api_key}"
            headers["x-api-key"] = api_key
        return headers

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
        if (
            self._client is not None
            and self._client != self._external_client
            and not self._client.is_closed
        ):
            await self._client.aclose()
            self._client = None

    async def check_health(self) -> JevHealthStatus:
        """Probe GET /health on the target TypeSafe service."""
        base_url = self.config.get_base_url()
        url = f"{base_url}/health"
        client = await self._get_client()
        headers = self._get_headers()

        if not self.config.api_key:
            return JevHealthStatus(
                status="unavailable",
                provider="typesafe",
                model=self.config.model,
                endpoint=url,
                has_api_key=False,
                details={"error": "Missing TYPESAFE_API_KEY"},
            )

        try:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                return JevHealthStatus(
                    status="ok",
                    provider="typesafe",
                    model=self.config.model,
                    endpoint=url,
                    has_api_key=True,
                    details=data if isinstance(data, dict) else {"response": response.text},
                )
            # If 404/405, server is reachable but /health might not be present on remote cloud
            if response.status_code in (404, 405):
                return JevHealthStatus(
                    status="ok",
                    provider="typesafe",
                    model=self.config.model,
                    endpoint=url,
                    has_api_key=True,
                    details={"notice": f"Server reachable (HTTP {response.status_code})"},
                )
            return JevHealthStatus(
                status="unavailable",
                provider="typesafe",
                model=self.config.model,
                endpoint=url,
                has_api_key=True,
                details={"http_status": response.status_code, "body": response.text},
            )
        except httpx.TimeoutException as exc:
            raise AgentFaultError(
                f"TypeSafe health check timed out after {self.config.connect_timeout_seconds}s at {url}"
            ) from exc
        except httpx.ConnectError as exc:
            raise AgentFaultError(
                f"TypeSafe service unreachable at {url}: {exc}"
            ) from exc
        except Exception as exc:
            if isinstance(exc, AgentFaultError):
                raise
            raise AgentFaultError(f"Unexpected error during TypeSafe health check: {exc}") from exc

    async def send_systemone(self, request: SystemOneRequest) -> SystemOneResponse:
        """Dispatch a SystemOneRequest to POST /v1/systemone with retry backoff."""
        if not self.config.api_key:
            raise AgentFaultError(
                "Missing TYPESAFE_API_KEY. Please provide an API key in .env or via JevConfig(api_key=...)."
            )

        url = self.config.get_effective_url()
        client = await self._get_client()
        headers = self._get_headers()

        payload = request.model_dump()
        if not payload.get("model"):
            payload["model"] = self.config.model

        max_attempts = max(1, self.config.max_retries + 1)
        last_error: Exception | None = None

        for attempt in range(max_attempts):
            t0 = time.perf_counter()
            try:
                response = await client.post(url, json=payload, headers=headers)
                elapsed_ms = (time.perf_counter() - t0) * 1000.0

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_systemone_response(data, elapsed_ms)

                # Authentication error (401 Unauthorized or 403 Forbidden) - non-retryable
                if response.status_code in (401, 403):
                    raise AgentFaultError(
                        f"TypeSafe authentication failed (HTTP {response.status_code}): {response.text}. "
                        "Verify TYPESAFE_API_KEY in .env."
                    )

                # Rate limit (429) or Service Overload (529) - retryable
                if response.status_code in (429, 529):
                    retry_after = float(response.headers.get("Retry-After", 0.5 * (2**attempt)))
                    logger.warning(
                        "TypeSafe API rate limit / overload (HTTP %d). Attempt %d/%d. Retrying in %.2fs",
                        response.status_code,
                        attempt + 1,
                        max_attempts,
                        retry_after,
                    )
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(retry_after)
                        continue
                    raise AgentFaultError(
                        f"TypeSafe rate limit / overload (HTTP {response.status_code}) "
                        f"exhausted after {max_attempts} attempts: {response.text}"
                    )

                # Other HTTP failures
                if attempt < max_attempts - 1 and response.status_code >= 500:
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue

                raise AgentFaultError(
                    f"TypeSafe inference failed with HTTP {response.status_code}: {response.text}"
                )

            except httpx.TimeoutException as exc:
                last_error = exc
                if attempt < max_attempts - 1:
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue
                raise AgentFaultError(
                    f"TypeSafe inference timed out after {self.config.timeout_seconds}s at {url}"
                ) from exc
            except httpx.ConnectError as exc:
                last_error = exc
                if attempt < max_attempts - 1:
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue
                raise AgentFaultError(
                    f"TypeSafe service unreachable at {url}: {exc}"
                ) from exc
            except Exception as exc:
                if isinstance(exc, AgentFaultError):
                    raise
                raise AgentFaultError(f"Unexpected error during TypeSafe inference: {exc}") from exc

        if last_error:
            raise AgentFaultError(f"TypeSafe inference failed: {last_error}") from last_error
        raise AgentFaultError("TypeSafe inference failed: Unknown error")

    def _parse_systemone_response(
        self, data: dict[str, Any], elapsed_ms: float
    ) -> SystemOneResponse:
        """Parse raw response JSON from TypeSafe System One API."""
        answers: dict[str, ChoiceAnswer] = {}
        model_name = str(data.get("model") or self.config.model)

        raw_answers = data.get("answers", {})
        if isinstance(raw_answers, dict):
            for q_id, q_ans in raw_answers.items():
                if isinstance(q_ans, dict):
                    choice = str(
                        q_ans.get("choice")
                        or q_ans.get("selected")
                        or q_ans.get("value")
                        or ""
                    )
                    confidence = float(q_ans.get("confidence", 1.0))
                    probs_raw = q_ans.get("probabilities") or q_ans.get("distribution") or {}
                    probabilities = {str(k): float(v) for k, v in probs_raw.items()}
                    answers[q_id] = ChoiceAnswer(
                        choice=choice,
                        confidence=confidence,
                        probabilities=probabilities,
                    )
                elif isinstance(q_ans, str):
                    answers[q_id] = ChoiceAnswer(choice=q_ans, confidence=1.0)

        # Fallback: if top-level dict contains question keys directly
        if not answers:
            for k, v in data.items():
                if (
                    k not in ("meta", "detail", "status", "model", "usage")
                    and isinstance(v, dict)
                    and "choice" in v
                ):
                    answers[k] = ChoiceAnswer.model_validate(v)

        usage: UsageInfo | None = None
        raw_usage = data.get("usage")
        if isinstance(raw_usage, dict):
            usage = UsageInfo(
                input_tokens=int(raw_usage.get("input_tokens", 0)),
                output_tokens=int(raw_usage.get("output_tokens", 0)),
            )

        meta: dict[str, Any] = data.get("meta", {})
        meta["latency_ms"] = elapsed_ms
        meta["model"] = model_name
        meta["provider"] = "typesafe"

        return SystemOneResponse(
            model=model_name,
            answers=answers,
            usage=usage,
            meta=meta,
        )
