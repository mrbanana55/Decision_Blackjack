# Implementation Plan: Laya Decision Agent Integration & Container Host Bridge

**Branch**: `005-laya-agent-integration` | **Date**: 2026-10-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-laya-agent-integration/spec.md`

## Summary

Integrate the locally hosted Laya model (`http://127.0.0.1:1234` on the host machine) into the Decision_Blackjack simulation platform. Encapsulate all communication, schemas, and agent adaptation within `backend/app/integrations/laya/`. Dynamically construct TypeSafe System One question schemas tailored to 5 distinct game situations (Paired Split, Initial Double/Surrender, Multi-card Draw, Insurance, and Round Wager Sizing) using table rules and context without hardcoded wagers or actions. Configure Docker Compose host bridging (`host.docker.internal:host-gateway`) and load `LAYA_BASE_URL` dynamically from `.env` to enable seamless communication across any host port.

---

## Technical Context

**Language/Version**: Python 3.12+ managed with `uv`

**Primary Dependencies**: `httpx` (async HTTP client), Pydantic v2 (serialization and schema validation), FastAPI, SQLAlchemy 2.0 AsyncIO

**Storage**: PostgreSQL 16 Alpine (`app_db`) for telemetry persistence and `/data/runs/` for JSON archives

**Testing**: `pytest`, `pytest-asyncio`, and `ruff` executed inside the Docker container (`docker compose exec backend uv run ...`)

**Target Platform**: Linux Docker container (`app_backend`) communicating with macOS host server (`http://host.docker.internal:<port>`)

**Project Type**: External AI provider adapter & simulation engine integration package

**Performance Goals**: End-to-end local inference turn latency under 300 ms; zero frame drops in orchestrator event processing

**Constraints**: RNF-02 fault pause compliance on network disconnects; TypeSafe System One JSON contract compliance; dynamic table minimum bet scaling; dynamic legal action filtering

**Scale/Scope**: 500+ round continuous simulation benchmarks without connection leaks or orchestrator deadlocks

---

## Constitution Check

*GATE: Evaluated against `.specify/memory/constitution.md`*

| Principle | Requirement | Plan Status |
|-----------|-------------|-------------|
| **I. Engine Independence & Determinism** | Blackjack rules must remain in backend core services without leakage into integrations. | **PASS**: Engine evaluates `legal_actions`; `LayaSchemaBuilder` consumes `legal_actions` without duplicating game mechanics. |
| **II. Tri-Entity Synchronization** | Laya, Jev, and Basic Strategy must compete under identical initial shoes and synchronize at round boundaries. | **PASS**: `LayaAgent` plugs into `SimulationOrchestrator` via `DecisionProvider` protocol. |
| **III. Provider Abstraction & Model Decoupling** | External model interactions must be encapsulated in dedicated adapter modules. HTTP failures must pause with state preservation (RNF-02). | **PASS**: All HTTP transport isolated in `backend/app/integrations/laya/`. Timeouts and errors raise `AgentFaultError` triggering graceful orchestrator pause. |
| **IV. Seeded Reproducibility** | Given identical seed, configuration, and entity responses, runs produce identical sequences. | **PASS**: Shoe and card distribution remain deterministic; model prompts and decisions are audited with full telemetry. |
| **V. Structured Telemetry & Batch Safety** | Every decision, confidence score, and latency must be stored in database and run archives. | **PASS**: Telemetry flows into `decisions` and `model_responses` persistence tables and WebSocket events. |

---

## Project Structure

### Documentation (`specs/005-laya-agent-integration/`)

```text
specs/005-laya-agent-integration/
├── plan.md                                # This implementation plan
├── research.md                            # Phase 0: Architecture, schema & bridge research
├── data-model.md                          # Phase 1: Pydantic models & situational schemas
├── quickstart.md                          # Phase 1: End-to-end test and validation workflows
├── contracts/
│   └── laya-systemone-api.md              # Contracts for 5 situational schemas & health probe
└── checklists/
    └── requirements.md                    # Quality requirements checklist
```

### Source Code (`backend/`)

```text
docker-compose.yml                         # Add extra_hosts host-gateway & LAYA_BASE_URL to backend

backend/app/integrations/
├── __init__.py                            # Integration package exports
└── laya/
    ├── __init__.py                        # Public exports (LayaAgent, LayaClient, LayaSchemaBuilder, LayaConfig)
    ├── config.py                          # LayaConfig reading LAYA_BASE_URL from .env with Docker host resolution
    ├── schemas.py                         # Pydantic models for System One requests, questions, answers, and health
    ├── builder.py                         # LayaSchemaBuilder generating situation-specific requests dynamically
    ├── client.py                          # Async HTTP client (httpx) for /health and /v1/systemone with retry logic
    └── agent.py                           # LayaAgent implementing DecisionProvider (turns, betting, insurance)

backend/tests/
├── test_laya_config.py                    # Unit tests for URL parsing and container bridge normalization
├── test_laya_schemas.py                   # Unit tests for 5 situational schemas with rule variations
├── test_laya_client.py                    # Integration tests for HTTP client, timeouts, and fault handling
├── test_laya_agent.py                     # Unit tests for LayaAgent DecisionProvider implementation
└── test_laya_simulation.py                # End-to-end simulation test integrating Laya with orchestrator & persistence
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

*No constitutional violations. Design strictly adheres to all architectural constraints.*
