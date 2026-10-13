# Technical Research & Architecture Decisions: Simulation Frontend API

**Feature**: `007-simulation-frontend-api`  
**Date**: 2026-10-12  
**Status**: Completed  

---

## 1. Executive Summary

This research document analyzes the technical design, protocol specifications, container networking strategies, and data serialization pipelines required to expose the Decision_Blackjack simulation engine to a web frontend.

The core objective is to provide:
1. **REST API** for experiment provisioning, casino rule customization ([`Reglas de BlackJack.md`](../../docs/Reglas%20de%20BlackJack.md)), historical run queries, data exports, and database maintenance.
2. **FastAPI Native WebSockets** (`fastapi.WebSocket`) for real-time telemetry event streaming and low-latency bidirectional flow control (`pause`, `resume`, `step`, `retry`, `stop`, `set_speed`).
3. **Container-to-Container & Browser Networking** ensuring seamless communication between the `app_frontend` container (Vite dev server) and `app_backend` container (FastAPI server).
4. **Hierarchical JSON Exporters** providing chunked, streaming downloads for both single-run datasets and full database archives.
5. **Database Purge Service** executing atomic cascading truncations across all 15 database tables with safety guards against clearing active runs.

---

## 2. Research Topics & Decisions

### Decision 1: Real-Time Communication Protocol & WebSocket Framework

- **Context**: The simulation generates high-frequency game events (opening wagers, card distributions, AI model inference results, and hand settlement). The frontend requires immediate updates and the ability to issue flow control commands.
- **Decision**: Use **FastAPI's native WebSocket support** (`from fastapi import WebSocket, WebSocketDisconnect`) with a centralized in-memory `SimulationConnectionManager`. Do NOT use `socket.io` or third-party socket wrappers.
- **Rationale**:
  - Eliminates extraneous client/server dependencies.
  - Zero-overhead integration with FastAPI's existing asyncio event loop.
  - Enables bidirectional messaging: server streams simulation events to clients; client pushes flow control commands (`pause`, `resume`, `step`, `retry`, `stop`, `set_speed`) over the same socket.
- **Alternatives Considered**:
  - *Socket.IO*: Explicitly rejected by user requirement; adds protocol framing overhead and requires matching frontend socket.io client versions.
  - *Server-Sent Events (SSE)*: Unidirectional only; would require separate HTTP POST endpoints for each flow control command, introducing latency and connection proliferation.

---

### Decision 2: Multi-Container Networking & CORS Architecture

- **Context**: In `docker-compose.yml`, the backend runs in `app_backend` (port 8000) and the frontend runs in `app_frontend` (port 5173) inside the bridge network `app_network`.
- **Decision**: Dual-path networking configuration:
  1. **Host/Browser Direct Path (Primary)**:
     - The user's web browser runs on the host OS.
     - Browser connects to frontend UI at `http://localhost:5173`.
     - Browser connects to backend REST API at `http://localhost:8000` and WebSocket at `ws://localhost:8000/ws/simulations/{session_id}`.
     - Configured via environment variable: `VITE_API_URL=http://localhost:8000` and `VITE_WS_URL=ws://localhost:8000`.
  2. **Container-to-Container Dev Proxy (Secondary / Seamless Fallback)**:
     - In Vite dev server configuration (`frontend/vite.config.ts`), configure server proxy:
       - `/api` → `http://backend:8000`
       - `/ws` → `ws://backend:8000`
     - Allows frontend code to make relative requests (`/api/...` and `/ws/...`) without hardcoded hostnames.
  3. **CORS Configuration**:
     - `CORSMiddleware` in `backend/app/main.py` explicitly allows:
       `["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://app_frontend:5173"]` with `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`.

---

### Decision 3: Simulation State & WebSocket Connection Manager

- **Context**: When a simulation runs in the background, multiple browser tabs or clients may observe it, and the simulation must react immediately to pause/speed commands.
- **Decision**: Implement `SimulationManager` in `backend/app/api/manager.py`:
  - **Session Registry**: Tracks active `SimulationOrchestrator` instances, their configuration, status, and background `asyncio.Task`.
  - **Socket Registry**: Maps `session_id` to `set[WebSocket]` connections.
  - **Event Bridge**: Subscribes to the orchestrator's `EventEmitter` (`SimulationEvent`) and serializes events to JSON frames:
    ```json
    {
      "event_type": "decision_made",
      "session_id": "sim-1234",
      "round": 3,
      "timestamp": "2026-10-12T21:30:00Z",
      "payload": { ... }
    }
    ```
  - **Pacing Delay**: Maintains a dynamic `delay_ms` attribute on active sessions (default 300 ms in visualized mode, adjustable from 0 ms to 2,000 ms via `set_speed`). When running in `fast_batch` mode, `delay_ms` is fixed to 0 ms and only simulation milestones are dispatched.
  - **Background Task Management**: Safely captures unhandled exceptions and transitions sessions to `PAUSED_ERROR` or `COMPLETED`.

---

### Decision 4: Rule Validation & Mapping to Core TableRules

- **Context**: The user specified that all changeable rules in [`docs/Reglas de BlackJack.md`](../../docs/Reglas%20de%20BlackJack.md) must be configurable via the initial POST payload.
- **Decision**: Define a comprehensive Pydantic v2 schema `TableRulesConfig` in `backend/app/api/schemas.py` that translates directly into engine `TableRules`:
  - `soft_17_rule`: `"S17"` (Stand on Soft 17) vs `"H17"` (Hit on Soft 17) → maps to `Soft17Rule`.
  - `blackjack_payout`: `1.5` (3:2), `1.2` (6:5), `1.0` (1:1).
  - `hole_card_rule`: `"AMERICAN_PEEK"` vs `"EUROPEAN_NO_HOLE_CARD"` → maps to `DealerStyle`.
  - `insurance_allowed`: `bool` (default `True`).
  - `surrender_rule`: `"LATE"`, `"EARLY"`, `"NO_SURRENDER"` → maps to `SurrenderRule`.
  - `double_after_split` (DAS): `bool` (default `True`).
  - `max_split_hands`: `int` between 1 and 4 (default 4).
  - `resplit_aces` (RSA): `bool` (default `False`).
  - `hit_split_aces`: `bool` (default `False`).
  - `num_decks`: `int` in `{1, 2, 4, 6, 8}` (default 6).
  - `penetration`: `float` between 0.50 and 0.85 (default 0.75).
  - `burn_cards_count`: `int` between 0 and 5 (default 0).
  - `min_bet`: `float >= 1.0` (default 10.0).
  - `max_bet`: `float >= min_bet` (default 500.0).
  - `initial_bankroll`: `float >= min_bet` (default 1000.0).
  - `stop_on_all_bankrupt`: `bool` (default `True`).
- **Pre-flight Entity Validation**:
  - Checks requested `entities` (`["optimal", "jev", "laya"]`).
  - If `mock_mode` is False and an entity is unreachable (e.g. `JevClient.check_health()` fails or `LayaClient.check_health()` fails), rejects with HTTP 422 giving explicit diagnostic failure reasons.

---

### Decision 5: Hierarchical JSON Export Implementation

- **Context**: User requires exporting single simulations or the full database to JSON.
- **Decision**:
  - **Single Simulation**: Reuse and enhance `RunExporter` from `backend/app/persistence/exporter.py`. Expose endpoint `GET /api/export/simulations/{session_or_run_id}`. Stream serialized JSON using FastAPI `StreamingResponse` with `Content-Disposition: attachment; filename="simulation_{id}_export.json"`.
  - **Full Database Export**: Implement `DatabaseExporter` in `backend/app/persistence/exporter.py` that queries all runs in descending chronological order and streams a JSON array of hierarchical run archives.
  - **Memory Protection**: Use an asynchronous generator to yield JSON chunks so database records are transformed and streamed incrementally without buffering hundreds of megabytes in memory.

---

### Decision 6: Database Reset / Purge Strategy

- **Context**: User requires a button to clear the database (delete every register in every table).
- **Decision**: Expose `DELETE /api/database` (and `POST /api/database/clear`):
  - **Safety Pre-condition**: Verify that `SimulationManager` has no sessions in `RUNNING` or `PAUSED` status. If active, return HTTP 409 Conflict.
  - **SQL Execution**: Execute `TRUNCATE TABLE runs RESTART IDENTITY CASCADE` on PostgreSQL. Because all child tables (`configurations`, `simulations`, `player_sessions`, `shoes`, `player_shoe_states`, `rounds`, `round_players`, `hands`, `card_events`, `bets`, `bankroll_transactions`, `hand_results`, `decisions`, `model_responses`) reference `runs` via `ON DELETE CASCADE` foreign keys, `TRUNCATE CASCADE` purges all 15 tables atomically in sub-second execution while resetting all primary key sequences.
  - **Response**: Return 200 OK with `{"status": "cleared", "tables_purged": 15, "timestamp": "..."}`.

---

## 3. Directory Layout Plan (`backend/app/api/`)

```text
backend/app/api/
├── __init__.py          # Package initialization
├── health.py            # Health probe router (existing GET /health)
├── schemas.py           # Pydantic v2 request/response models
├── manager.py           # Session & WebSocket ConnectionManager
├── simulations.py       # REST router: POST/GET /api/simulations
├── websocket.py         # WebSocket router: /ws/simulations/{session_id}
├── export.py            # Export router: GET /api/export/*
├── database.py          # Maintenance router: DELETE /api/database
└── router.py            # Main API router consolidating all endpoints
```
