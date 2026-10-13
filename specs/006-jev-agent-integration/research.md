# Phase 0 Research: Jev Decision Agent Integration & Remote System One Provider

**Feature Branch**: `006-jev-agent-integration`  
**Date**: 2026-10-12  
**Status**: Completed  

---

## 1. Executive Summary

This research establishes the architectural decisions, protocol contracts, and resilience patterns required to integrate TypeSafe's flagship model **Jev** into the Decision_Blackjack multi-agent simulation framework. The integration will reside in `backend/app/integrations/jev/`, mirroring the clean decoupling established for Laya in `backend/app/integrations/laya/`.

---

## 2. Technical Decisions & Analysis

### Decision 1: Transport & Client Architecture
- **Decision**: Implement `JevClient` using `httpx.AsyncClient` supporting connection pooling, keep-alive, configurable timeouts, and Bearer authorization.
- **Rationale**: The simulation orchestrator operates entirely asynchronously on `asyncio`. `httpx` is already an established core dependency in the project and provides first-class async HTTP request support with clean error hierarchies (`TimeoutException`, `ConnectError`, `HTTPStatusError`).
- **Alternatives Considered**:
  - `requests`: Rejected because it is blocking and would freeze the orchestrator round barrier.
  - `aiohttp`: Rejected because `httpx` is already utilized throughout the codebase.

### Decision 2: Credential & Endpoint Configuration
- **Decision**: Define `JevConfig` in `backend/app/integrations/jev/config.py` using Pydantic v2 `BaseModel`, dynamically reading from `.env`:
  - `TYPESAFE_API_KEY`: API key for Bearer authentication.
  - `TYPESAFE_API_URL`: Target endpoint (default: `https://api.typesafe.ai/v1/systemone`).
  - `TYPESAFE_MODEL`: Model alias to evaluate (default: `jev-latest`).
  - `TYPESAFE_TIMEOUT_SECONDS`: Request timeout (default: 15.0s).
  - `TYPESAFE_CONNECT_TIMEOUT_SECONDS`: Connection establishment timeout (default: 3.0s).
  - `TYPESAFE_MAX_RETRIES`: Rate-limit and transient retry count (default: 3).
- **Rationale**: Adheres strictly to Constitution Principle III ("API keys and secrets MUST be loaded from environment variables (`.env`) and MUST NEVER be exposed to the frontend client or committed to version control").
- **Alternatives Considered**: Hardcoded configuration or direct `os.getenv` calls scattered across files; rejected to ensure centralized validation and testability.

### Decision 3: TypeSafe System One Request/Response Contract
- **Decision**: Define request and response models in `backend/app/integrations/jev/schemas.py`:
  - Top-level request contains:
    - `state` (str): Observable table context.
    - `model` (str): Model name (e.g. `jev-latest`).
    - `questions` (dict[str, ChoiceQuestion]): Named questions map.
  - Choice question contains:
    - `type`: `"choice"`.
    - `instructions` (str): Judgment prompt.
    - `criteria` (dict[str, str]): Candidate option keys mapped to descriptions.
  - Top-level response contains:
    - `model` (str): Evaluating model revision.
    - `answers` (dict[str, ChoiceAnswer]): Answer containing `choice` (str), `probabilities` (dict[str, float]), and `confidence` (float).
    - `usage` (dict[str, int]): Token counts (`input_tokens`, `output_tokens`).
- **Rationale**: Strictly complies with the live TypeSafe System One specification (`https://docs.typesafe.ai/api.md`). The parser will also support `distribution` as a fallback alias for `probabilities` to maintain protocol interchangeability with Laya.

### Decision 4: Rate Limiting & Overload Resilience (HTTP 429 & 529)
- **Decision**: Implement automated exponential backoff with jitter in `JevClient` for HTTP 429 (`Too Many Requests`) and HTTP 529 (`Overloaded`) up to `TYPESAFE_MAX_RETRIES`. If retries are exhausted or a non-retryable 4xx/5xx occurs (e.g. HTTP 401 Unauthorized), translate immediately to `AgentFaultError`.
- **Rationale**: Fulfills Constitution Principle II, III, and RNF-02. Transient cloud rate spikes will resolve automatically; persistent failures cleanly trigger `PAUSED_ERROR` in the orchestrator without data corruption.
- **Alternatives Considered**: Failing immediately without retries; rejected because transient rate limiting is normal for cloud API endpoints.

### Decision 5: Dynamic Situational Prompts
- **Decision**: Implement `JevSchemaBuilder` in `backend/app/integrations/jev/builder.py` providing:
  - Situation 1A: Initial Paired Hand (Split Eligible, Surrender Disabled)
  - Situation 1B: Initial Paired Hand (Split Eligible, Surrender Enabled)
  - Situation 2A: Initial Standard Hand (Double Eligible, Surrender Disabled)
  - Situation 2B: Initial Standard Hand (Double & Surrender Enabled)
  - Situation 3: Multi-Card Draw Hand (Post-Hit / 3+ Cards: strictly `hit` & `stand`)
  - Situation 4: Insurance Phase (Dealer exposed Ace: `accept` vs `decline`)
  - Situation 5: Round Betting Phase (Pre-deal wager sizing: `1x`, `2x`, `4x`, `8x` table minimum bet)
- **Rationale**: Ensures Jev receives the exact same tactical information and criteria definitions as Laya, guaranteeing a fair and scientifically valid comparison.

### Decision 6: Health Diagnostic Endpoint (`/health/jev`)
- **Decision**: Expose `GET /health/jev` in `backend/app/api/health.py` that verifies:
  - Presence of `TYPESAFE_API_KEY`.
  - Target URL resolution.
  - Lightweight connectivity probe or credentials validation.
- **Rationale**: Allows operators to confirm that Jev is operational before starting simulations.

---

## 3. Risk Assessment & Mitigations

| Risk | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **API Key Missing or Expired** | High (Simulation cannot run) | `JevConfig` validates key presence on startup; `/health/jev` reports diagnostic warning; client raises descriptive `AgentFaultError`. |
| **Cloud Network Latency Spikes** | Medium (Delays round barrier) | Configurable timeout (`TYPESAFE_TIMEOUT_SECONDS=15.0`) prevents deadlocks; latency metric recorded per inference. |
| **Rate Limit (HTTP 429) During Multi-Round Sim** | Medium (Simulation paused) | Exponential backoff retry reduces pause frequency; when exhausted, clean pause (`PAUSED_ERROR`) preserves all progress. |
| **Schema Divergence between Jev and Laya** | High (Invalid comparative benchmark) | Both agents share identical situational categorization, state formatting, criteria descriptions, and action mappings. |
