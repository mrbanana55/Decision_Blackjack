# Implementation Plan: Simulation Frontend API & Export Service

**Branch**: `007-simulation-frontend-api` | **Date**: 2026-10-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/007-simulation-frontend-api/spec.md`

---

## Summary

This feature designs and implements the full-stack communication layer between the Decision_Blackjack simulation engine and the web frontend client. Residing inside `backend/app/api/`, it leverages native **FastAPI** (`fastapi.FastAPI`, `fastapi.APIRouter`) and native **WebSockets** (`fastapi.WebSocket`) without third-party socket wrappers. 

Key capabilities include:
1. **Experiment Provisioning & Rules Setup**: `POST /api/simulations` validating and applying all changeable casino rules from [`Reglas de BlackJack.md`](../../docs/Reglas%20de%20BlackJack.md) (Soft 17, Natural Blackjack payouts, Peek/ENHC, insurance, surrender, DAS, RSA, split limits, decks, penetration, burn cards, bankrolls, table betting boundaries, execution modes).
2. **Live Decision Telemetry & Strategy Deviation Analytics**: Bidirectional WebSocket endpoint `/ws/simulations/{session_id}` streaming turn-by-turn decisions for Jev, Laya, and Basic Strategy with full inference metadata (confidence, probabilities, latency, tokens) and rich Basic Strategy comparison payloads (`DecisionComparison`: optimal action, actual action, category, reasoning). Live running strategy deviation statistics (optimality rates, category breakdowns across Hard Totals, Soft Totals, Pair Splits, Surrenders, and bet spread deltas) are streamed in round settlement frames and queryable via `GET /api/simulations/{session_id}/deviations`.
3. **Interactive Flow Control**: Native WebSocket and REST commands (`pause`, `resume`, `step`, `retry`, `stop`, `set_speed`) enabling dynamic round pacing adjustment (0 ms to 2,000 ms) without interrupting execution.
4. **Cross-Container Networking**: Seamless communication between `app_frontend` (Vite, port 5173) and `app_backend` (FastAPI, port 8000) inside `app_network` and over host localhost.
5. **Hierarchical JSON Exporters**: `GET /api/export/simulations/{id}` and `GET /api/export/database` with streamed chunked responses.
6. **Database Maintenance & Purge**: `DELETE /api/database` / `POST /api/database/clear` executing atomic cascading table truncation with safety guards against active simulations.

---

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript (frontend)  
**Primary Dependencies**: FastAPI (>=0.115.0), Pydantic v2 (>=2.10.0), Starlette WebSockets, SQLAlchemy 2.0 (asyncpg), httpx  
**Storage**: PostgreSQL 16 (15-table relational schema in `backend/app/persistence/models.py`)  
**Testing**: pytest, pytest-asyncio, `starlette.testclient.TestClient`, `httpx.AsyncClient`  
**Target Platform**: Docker containerized Linux environment (`app_backend:8000`, `app_frontend:5173`, bridge `app_network`)  
**Project Type**: Web service (FastAPI REST & WebSocket API)  
**Performance Goals**: Event dispatch latency < 150 ms; single simulation JSON export < 3 s; full database export memory < 256 MB  
**Constraints**: Native FastAPI WebSockets strictly (no socketio); CORS support across Docker network and browser host; RNF-02 fault recovery  
**Scale/Scope**: Up to 100,000 rounds per simulation; 1 to 1,000 simulations; 3 parallel decision entities; 15 database tables  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Requirement | Compliance Status | Analysis |
| :--- | :--- | :---: | :--- |
| **I. Engine Independence & Determinism** | Engine MUST remain deterministic and UI-agnostic; no game logic in frontend. | **PASS** | Game logic executes exclusively in `backend/app/engine` and `backend/app/simulation`. The API only serializes state, streams events, and accepts configuration. |
| **II. Tri-Entity Synchronization** | Jev, Laya, and Optimal Strategy evaluated in isolated tables with identical initial shoes and round synchronization. | **PASS** | Orchestrator creates isolated `EntityTable`s from identical generation-0 shoes; WebSocket broadcast events are synchronized per round. |
| **III. Provider Abstraction & Model Decoupling** | Decision entities implement `DecisionProvider`; API keys loaded from `.env` and never exposed. | **PASS** | API interacts via `DecisionProvider` protocol; secrets remain isolated in backend `.env`; pre-flight checks verify connectivity without leaking keys. |
| **IV. Seeded Reproducibility** | Every simulation run MUST support deterministic seed configuration. | **PASS** | `POST /api/simulations` accepts an explicit `seed` parameter; identical seeds produce identical shoe and decision trajectories. |
| **V. Telemetry & Persistence** | Telemetry latency < 200 ms; persistence to PostgreSQL; exportable to JSON. | **PASS** | WebSocket dispatch target is < 150 ms; `SimulationPersistenceListener` saves relational records; hierarchical JSON export is provided for single runs and full database. |

---

## Project Structure

### Documentation (`specs/007-simulation-frontend-api/`)

```text
specs/007-simulation-frontend-api/
├── spec.md                     # Feature specification (validated with 16/16 checklist items)
├── plan.md                     # This implementation plan
├── research.md                 # Technical research, architecture decisions & protocol trade-offs
├── data-model.md               # Pydantic v2 models, WebSocket message frames, export schemas
├── quickstart.md               # Runnable validation scenarios (REST, WebSocket, Export, Purge)
├── contracts/
│   ├── rest-api.yaml           # OpenAPI 3.1 specification for all REST endpoints
│   └── websocket-protocol.md   # WebSocket bidirectional protocol framing and event catalog
└── tasks.md                    # Actionable task breakdown (Phase 2 output via /speckit-tasks)
```

### Source Code (`backend/`)

```text
backend/app/
├── api/
│   ├── __init__.py             # API package exports
│   ├── health.py               # Health probe router (GET /health, GET /health/laya)
│   ├── schemas.py              # Pydantic v2 request/response models for all endpoints
│   ├── manager.py              # SimulationManager (WebSocket connections, session registry, event bridge)
│   ├── simulations.py          # REST endpoints (POST /api/simulations, GET /api/simulations, control)
│   ├── websocket.py            # Native WebSocket endpoint (/ws/simulations/{session_id})
│   ├── export.py               # Export endpoints (GET /api/export/simulations/{id}, GET /api/export/database)
│   ├── database.py             # Maintenance endpoints (DELETE /api/database, POST /api/database/clear)
│   └── router.py               # Consolidated API router mounted in main.py
├── persistence/
│   ├── exporter.py             # Extended with DatabaseExporter for streaming full-database export
│   └── ...                     # Existing database, models, listener, repositories
├── main.py                     # Configures CORS, mounts api_router, registers lifespan hooks
└── ...

backend/tests/
├── test_api_schemas.py         # Schema validation, default rules, constraint enforcement
├── test_api_simulations.py     # Provisioning, retrieval, listing, control, and strategy deviation endpoints
├── test_api_websocket.py       # WebSocket connection lifecycle, event streaming, client commands, deviation telemetry
├── test_api_export.py          # Single-run and full-database hierarchical JSON export
└── test_api_database.py        # Database purge execution and active simulation conflict guards
```

---

## Complexity Tracking

*No constitutional violations identified. No unjustified architectural complexity.*

| Pattern / Component | Purpose | Justification |
| :--- | :--- | :--- |
| **In-Memory SimulationManager** | Manages WebSocket connections and orchestrator handles in process memory | Required for low-latency dispatch (<150ms) between orchestrator `EventEmitter` and native `fastapi.WebSocket` clients without Redis broker overhead. |
| **Database TRUNCATE CASCADE** | High-performance purge across all 15 tables | Leverages PostgreSQL relational schema foreign keys to reset all data atomically in sub-second time. |
