# Implementation Plan: Jev Decision Agent Integration & Remote System One Provider

**Branch**: `006-jev-agent-integration` | **Date**: 2026-10-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/006-jev-agent-integration/spec.md`

## Summary

Integrate TypeSafe's flagship model **Jev** into the Decision_Blackjack simulation platform as an autonomous decision provider. Encapsulate all remote communication, Bearer token authentication, rate-limiting retry backoff, response parsing, and schema generation within `backend/app/integrations/jev/`. Dynamically construct TypeSafe System One question schemas tailored to all 5 distinct game situations (Paired Split, Initial Double/Surrender, Multi-card Draw, Insurance, and Round Wager Sizing) without hardcoded wagers or actions. Sourced dynamically from `.env` (`TYPESAFE_API_KEY`, `TYPESAFE_API_URL`, `TYPESAFE_MODEL`), Jev seamlessly interoperates with the orchestrator, persistence layer, and decision comparator.

---

## Technical Context

**Language/Version**: Python 3.12+ managed with `uv`

**Primary Dependencies**: `httpx` (async HTTP client with connection pooling), Pydantic v2 (serialization and schema validation), FastAPI, SQLAlchemy 2.0 AsyncIO

**Storage**: PostgreSQL 16 Alpine (`app_db`) for telemetry persistence and `/data/runs/` for JSON archives

**Testing**: `pytest`, `pytest-asyncio`, and `ruff` executed inside the Docker container (`docker compose exec backend uv run ...`)

**Target Platform**: Linux Docker container (`app_backend`) communicating over HTTPS with remote TypeSafe System One API (`https://api.typesafe.ai/v1/systemone`)

**Project Type**: External AI provider adapter & simulation engine integration package

**Performance Goals**: End-to-end inference turn latency under 1500 ms; bounded backoff retries on rate limits; zero frame drops in orchestrator event processing

**Constraints**: RNF-02 fault pause compliance on network disconnects or rate limit exhaustion; TypeSafe System One JSON contract compliance with Bearer auth; dynamic table minimum bet scaling; dynamic legal action filtering

**Scale/Scope**: 500+ round continuous simulation benchmarks without connection leaks or orchestrator deadlocks

---

## Constitution Check

_GATE: Evaluated against `.specify/memory/constitution.md`_

| Principle                                        | Requirement                                                                                                                                                               | Plan Status                                                                                                                                                                                                                                 |
| :----------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **I. Engine Independence & Determinism**         | Blackjack rules must remain in backend core services without leakage into integrations.                                                                                   | **PASS**: Engine evaluates `legal_actions`; `JevSchemaBuilder` consumes `legal_actions` without duplicating game mechanics.                                                                                                                 |
| **II. Tri-Entity Synchronization**               | Jev, Laya, and Basic Strategy must compete under identical initial shoes and synchronize at round boundaries.                                                             | **PASS**: `JevAgent` implements `DecisionProvider` protocol and runs within `SimulationOrchestrator` under identical shoes.                                                                                                                 |
| **III. Provider Abstraction & Model Decoupling** | External model interactions must be encapsulated in dedicated adapter modules. API keys must load from `.env`. HTTP failures must pause with state preservation (RNF-02). | **PASS**: All HTTP transport isolated in `backend/app/integrations/jev/`. API key loaded from `TYPESAFE_API_KEY` in `.env`. Timeouts, rate limit exhaustion, or HTTP errors raise `AgentFaultError` triggering graceful orchestrator pause. |
| **IV. Seeded Reproducibility**                   | Given identical seed, configuration, and entity responses, runs produce identical sequences.                                                                              | **PASS**: Shoe and card distribution remain deterministic; model prompts and decisions are audited with full telemetry.                                                                                                                     |
| **V. Structured Telemetry & Batch Safety**       | Every decision, confidence score, and latency must be stored in database and run archives.                                                                                | **PASS**: Telemetry flows into `decisions` and `model_responses` (`provider=ModelProvider.SYSTEM_ONE`) persistence tables and WebSocket events.                                                                                             |

---

## Project Structure

### Documentation (`specs/006-jev-agent-integration/`)

```text
specs/006-jev-agent-integration/
├── plan.md                                # This implementation plan
├── research.md                            # Phase 0: Architecture, schema & retry research
├── data-model.md                          # Phase 1: Pydantic models & situational schemas
├── quickstart.md                          # Phase 1: End-to-end test and validation workflows
├── contracts/
│   └── jev-systemone-api.md               # Contracts for 5 situational schemas & health probe
└── checklists/
    └── requirements.md                    # Quality requirements checklist
```

### Source Code (`backend/`)

```text
backend/app/integrations/
├── __init__.py                            # Integration package exports (exposing JevAgent, LayaAgent)
└── jev/
    ├── __init__.py                        # Public exports (JevAgent, JevClient, JevSchemaBuilder, JevConfig)
    ├── config.py                          # JevConfig reading TYPESAFE_API_KEY, TYPESAFE_API_URL, TYPESAFE_MODEL
    ├── schemas.py                         # Pydantic models for System One requests, questions, answers, usage, health
    ├── builder.py                         # JevSchemaBuilder generating situation-specific requests dynamically
    ├── client.py                          # Async HTTP client (httpx) for /v1/systemone with retry backoff & Bearer auth
    └── agent.py                           # JevAgent implementing DecisionProvider (turns, betting, insurance)

backend/app/api/
└── health.py                              # Add GET /health endpoint

backend/app/simulation/
└── __init__.py                            # Expose JevAgent alongside LayaAgent

backend/tests/
├── test_jev_config.py                     # Unit tests for JevConfig validation and defaults
├── test_jev_schemas.py                    # Unit tests for situational schemas with rule variations
├── test_jev_client.py                     # Integration tests for HTTP client, retries, backoff, and errors
├── test_jev_agent.py                      # Unit tests for JevAgent DecisionProvider implementation
└── test_jev_simulation.py                 # End-to-end simulation test integrating Jev with orchestrator & persistence
```

---

## Situational Schemas Planned

1. **Initial Paired Hand (Split Eligible, Surrender Disabled)**: Hand has 2 matching cards, bankroll $\ge$ bet, surrender disabled. Includes `hit`, `stand`, `split`, and conditionally `double` if DAS allowed.
2. **Initial Paired Hand (Split Eligible, Surrender Enabled)**: Hand has 2 matching cards, bankroll $\ge$ bet, late surrender allowed. Includes `hit`, `stand`, `split`, `surrender`, and conditionally `double` if DAS allowed.
3. **Initial Standard Hand (Double Eligible, Surrender Disabled)**: Hand has 2 non-matching cards, surrender disabled. Includes `hit`, `stand`, and `double`.
4. **Initial Standard Hand (Double & Surrender Enabled)**: Hand has 2 non-matching cards, late surrender allowed. Includes `hit`, `stand`, `double`, and `surrender`.
5. **Multi-Card Draw Hand (Post-Hit / 3+ Cards)**: Player has drawn cards. Double, split, and surrender are prohibited. Strictly `hit` and `stand`.
6. **Insurance Phase (Dealer Ace Revealed)**: Pre-play phase. Question specifically evaluates `accept` vs `decline`.
7. **Round Betting Phase (Pre-Deal Wager Sizing)**: Dynamically scales wagers based on `TableRules.min_bet` (`1x`, `2x`, `4x`, `8x`).

---

## Complexity Tracking

_No constitutional violations. Design strictly adheres to all architectural constraints._
