# Tasks: Simulation Frontend API & Export Service

**Branch**: `007-simulation-frontend-api` | **Date**: 2026-10-12 | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Package structure initialization and API configuration

- [x] T001 Initialize API package directory structure and module files in `backend/app/api/` (`schemas.py`, `manager.py`, `simulations.py`, `websocket.py`, `export.py`, `database.py`, `router.py`)
- [x] T002 Configure CORS middleware and mount consolidated API router in `backend/app/main.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core schemas, in-memory session manager, and routing infrastructure required by all user stories

**⚠️ CRITICAL**: No user story implementation can begin until this foundational phase is complete.

- [x] T003 [P] Implement Pydantic v2 schemas in `backend/app/api/schemas.py` defining:
  - `TableRulesConfig` with verbatim constraints: `soft_17_rule` ("S17" or "H17", default "S17"), `blackjack_payout` (float 1.0 to 2.0, default 1.5), `hole_card_rule` ("AMERICAN_PEEK" or "EUROPEAN_NO_HOLE_CARD", default "AMERICAN_PEEK"), `insurance_allowed` (bool, default True), `surrender_rule` ("LATE", "EARLY", or "NO_SURRENDER", default "LATE"), `double_after_split` (bool, default True), `max_split_hands` (int 1 to 4, default 4), `resplit_aces` (bool, default False), `hit_split_aces` (bool, default False), `num_decks` (int 1, 2, 4, 6, 8, default 6), `penetration` (float 0.50 to 0.85, default 0.75), `burn_cards_count` (int 0 to 5, default 0), `initial_bankroll` (float 100.0 to 1,000,000.0, default 1000.0), `min_bet` (float 1.0 to 1000.0, default 10.0), `max_bet` (float 10.0 to 50000.0, default 500.0), and `stop_on_all_bankrupt` (bool, default True)
  - `SimulationConfigRequest` with verbatim constraints: `max_rounds` (int 1 to 100000, default 10), `num_simulations` (int 1 to 1000, default 1), `execution_mode` ("visualized" or "fast_batch", default "visualized"), `delay_ms` (float 0.0 to 2000.0, default 300.0), `seed` (int or None, default None), `entities` (list of str, subset of ["optimal", "jev", "laya"], default ["optimal", "jev", "laya"]), and `mock_mode` (bool, default False)
  - Response models: `SimulationResponse`, `SimulationListItem`, `SimulationListResponse`, `PurgeDatabaseResponse`, and `ErrorResponse`
- [x] T004 [P] Implement schema and validation unit tests in `backend/tests/test_api_schemas.py` validating valid configurations, default values, and rule boundary violations (e.g. min_bet > max_bet, penetration out of bounds)
- [x] T005 Implement `SimulationManager` in `backend/app/api/manager.py` to register active simulation sessions, manage WebSocket connection registries per session, coordinate orchestrator lifecycle, and dispatch events
- [x] T006 Implement API router consolidation in `backend/app/api/router.py` mounting sub-routers for simulations, export, maintenance, and health, and verify application startup via `backend/tests/test_health.py`

**Checkpoint**: Foundation ready - request validation, session management, and routing structure are fully operational.

---

## Phase 3: User Story 1 - Configurable Experiment Initialization & Casino Rules Setup (Priority: P1) 🎯 MVP

**Goal**: Enable frontend users to configure, customize all house rules from `docs/Reglas de BlackJack.md`, and initialize reproducible multi-agent Blackjack simulations with identical starting shoes across Jev, Laya, and Basic Strategy.

**Independent Test**: Submit a valid configuration payload to `POST /api/simulations`, verify rules validation, entity pre-flight health checks, deterministic shoe seeding, and receipt of HTTP 201 Created with session details and WebSocket connection URL.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T007 [P] [US1] Create simulation provisioning tests in `backend/tests/test_api_simulations.py` testing successful creation (HTTP 201), rule validation failures (HTTP 422), custom rule persistence, and default values application

### Implementation for User Story 1

- [x] T008 [US1] Implement entity pre-flight health verification and provider factory in `backend/app/api/simulations.py` validating connectivity for requested entities (`optimal`, `jev`, `laya`) with `mock_mode` fallback
- [x] T009 [US1] Implement `POST /api/simulations` endpoint in `backend/app/api/simulations.py` creating isolated `EntityTable`s with identical shoes, initializing the simulation session, registering it in `SimulationManager`, and returning HTTP 201 `SimulationResponse`
- [x] T010 [US1] Mount simulations router in `backend/app/api/router.py` and verify all tests pass in `backend/tests/test_api_simulations.py`

**Checkpoint**: User Story 1 (MVP) is fully functional and independently testable.

---

## Phase 4: User Story 2 - Real-Time Multi-Agent Simulation Streaming & Strategy Deviation Analytics (Priority: P1)

**Goal**: Broadcast live round telemetry over native WebSockets (`/ws/simulations/{session_id}`) with turn-by-turn decisions for Jev, Laya, and Basic Strategy, embedding rich Basic Strategy comparison payloads (`DecisionComparison`) and computing real-time strategy deviation statistics per player.

**Independent Test**: Connect a WebSocket client to `/ws/simulations/{session_id}`, trigger simulation start, verify receipt of `SESSION_SNAPSHOT`, `ROUND_STARTED`, `BET_PLACED`, `CARD_DEALT`, `DECISION_MADE` (with nested `comparison`), and `ROUND_SETTLED` (with `running_deviations`), then query `GET /api/simulations/{session_id}/deviations`.

### Tests for User Story 2 ⚠️

- [x] T011 [P] [US2] Create WebSocket connection and telemetry streaming tests in `backend/tests/test_api_websocket.py` verifying connection handshake, 4404 close on non-existent session, ordered event sequence, and strategy deviation calculations

### Implementation for User Story 2

- [x] T012 [P] [US2] Implement strategy deviation schemas and tracker models in `backend/app/api/schemas.py`:
  - `DecisionComparisonPayload` (`is_optimal`, `optimal_action`, `actual_action`, `category`, `reasoning`, `is_legal`)
  - `CategoryDeviationStats` (`total_decisions`, `deviations`, `optimality_rate`)
  - `BetSpreadDeviationStats` (`total_bets`, `suboptimal_bets`, `total_bet_delta`, `avg_bet_delta`)
  - `EntityDeviationStats` (`entity_id`, `total_decisions`, `optimal_decisions`, `deviations_count`, `optimality_rate`, `categories`, `betting_deviations`)
  - `SimulationDeviationsResponse` (`session_id`, `current_round`, `entities`, `updated_at`)
- [x] T013 [US2] Implement background simulation execution loop and telemetry bridge in `backend/app/api/manager.py` that listens to orchestrator events, embeds `DecisionComparison` into `DECISION_MADE`, accumulates running category deviations (`hard_total`, `soft_total`, `pair_split`, `surrender`, `insurance`) and bet spread deltas, and broadcasts frames to connected WebSockets
- [x] T014 [US2] Implement native FastAPI WebSocket endpoint `/ws/simulations/{session_id}` in `backend/app/api/websocket.py` handling client connections, immediate `SESSION_SNAPSHOT` emission, and event streaming
- [x] T015 [US2] Implement dedicated analytics endpoint `GET /api/simulations/{session_id}/deviations` in `backend/app/api/simulations.py` returning real-time strategy deviation metrics for all active entities
- [x] T016 [US2] Mount WebSocket router in `backend/app/api/router.py` and verify telemetry streaming and deviation analytics in `backend/tests/test_api_websocket.py`

**Checkpoint**: User Stories 1 AND 2 are fully functional and synchronized. Live turn-by-turn telemetry and strategy deviation analytics stream to connected clients.

---

## Phase 5: User Story 3 - Interactive Simulation Flow Control & Fault Recovery (Priority: P2)

**Goal**: Allow frontend clients to pause, resume, single-step, dynamically adjust round pacing delay (`set_speed`), stop execution, and recover from external AI agent timeouts or rate limits (`retry`).

**Independent Test**: Connect via WebSocket or REST control endpoint, send `pause` and verify simulation halts at round boundary, send `set_speed` with new delay and verify updated pacing, send `step` and verify single-round advancement, simulate an agent fault to verify transition to `PAUSED_ERROR`, and send `retry` to resume cleanly.

### Tests for User Story 3 ⚠️

- [x] T017 [P] [US3] Create flow control and fault recovery tests in `backend/tests/test_api_websocket.py` and `backend/tests/test_api_simulations.py` testing `pause`, `resume`, `step`, `set_speed`, `stop`, and RNF-02 `retry` on error

### Implementation for User Story 3

- [x] T018 [US3] Implement client command dispatching in `backend/app/api/websocket.py` supporting `pause`, `resume`, `step` (round/turn), `set_speed` (validating `delay_ms` between 0.0 and 2000.0), `stop`, and `retry`
- [x] T019 [US3] Implement REST control endpoint `POST /api/simulations/{session_id}/control` in `backend/app/api/simulations.py` accepting `ControlCommandRequest` as a fallback to WebSocket commands
- [x] T020 [US3] Implement RNF-02 fault recovery handler in `backend/app/api/manager.py` transitioning simulation session to `PAUSED_ERROR`, preserving accumulated metrics and bankroll state upon provider timeout or HTTP 429, and executing `retry` or `abort`

**Checkpoint**: Full bidirectional flow control and fault recovery operational.

---

## Phase 6: User Story 4 - Granular and Comprehensive Database JSON Data Export (Priority: P2)

**Goal**: Export stored simulation records from the relational database as structured hierarchical JSON files—either a single simulation run via `GET /api/export/simulations/{session_or_run_id}` or the full database archive via `GET /api/export/database` with streamed chunked serialization.

**Independent Test**: Complete a simulation run, request `GET /api/export/simulations/{id}` and confirm downloading formatted JSON matching `RunExporter` schema with attachment headers; request `GET /api/export/database` and verify streaming archive download without memory bloat.

### Tests for User Story 4 ⚠️

- [x] T021 [P] [US4] Create export endpoint tests in `backend/tests/test_api_export.py` testing single-run export (HTTP 200 with valid schema, HTTP 404 for missing run) and full-database export streaming
- [x] T022 [US4] Extend `RunExporter` in `backend/app/persistence/exporter.py` with `export_all_runs_streaming()` yielding JSON chunks incrementally to guarantee server memory stays under 256 MB for high-volume datasets
- [x] T023 [US4] Implement single simulation export endpoint `GET /api/export/simulations/{session_or_run_id}` in `backend/app/api/export.py` with `Content-Disposition: attachment; filename="simulation_<ID>_export.json"` header
- [x] T024 [US4] Implement full database export endpoint `GET /api/export/database` in `backend/app/api/export.py` using FastAPI `StreamingResponse` with `Content-Disposition: attachment; filename="decision_blackjack_full_export_<TIMESTAMP>.json"` header
- [x] T025 [US4] Mount export router in `backend/app/api/router.py` and verify all export tests pass in `backend/tests/test_api_export.py`

**Checkpoint**: Data export endpoints fully functional for both granular and archival use cases.

---

## Phase 7: User Story 5 - Historical Runs Catalog & Benchmark Analytics (Priority: P3)

**Goal**: Enable users to browse past simulation runs, view summary benchmark metrics (net profit, win rates, optimality percentages), and inspect detailed round results for completed runs.

**Independent Test**: Query `GET /api/simulations` with pagination and verify list of completed runs with metrics; query `GET /api/simulations/{session_id}` and verify detailed run breakdown.

### Tests for User Story 5 ⚠️

- [x] T026 [P] [US5] Create historical runs catalog tests in `backend/tests/test_api_simulations.py` testing paginated listing (`page`, `page_size`) and detailed run inspection

### Implementation for User Story 5

- [x] T027 [US5] Implement paginated catalog endpoint `GET /api/simulations` in `backend/app/api/simulations.py` querying database runs through `SimulationRepository` and returning `SimulationListResponse`
- [x] T028 [US5] Implement detailed simulation inspection endpoint `GET /api/simulations/{session_id}` in `backend/app/api/simulations.py` returning complete run descriptor, table rules snapshot, player benchmarks, and deviation summaries

**Checkpoint**: Historical runs exploration and benchmarking endpoints fully operational.

---

## Phase 8: User Story 6 - Database Purge & Storage Reset (Priority: P3)

**Goal**: Provide a maintenance endpoint (`DELETE /api/database` / `POST /api/database/clear`) that purges all records across all 15 relational tables while blocking execution with HTTP 409 Conflict if simulations are actively running.

**Independent Test**: Complete several simulation runs, call `DELETE /api/database`, verify all 15 tables are cleared and HTTP 200 returned; launch an active simulation, attempt purge, and verify HTTP 409 Conflict rejection.

### Tests for User Story 6 ⚠️

- [x] T029 [P] [US6] Create database purge tests in `backend/tests/test_api_database.py` testing successful purge (HTTP 200), table emptiness verification, and active simulation conflict guard (HTTP 409)

### Implementation for User Story 6

- [x] T030 [US6] Implement cascading purge repository method `purge_all_tables()` in `backend/app/persistence/repository.py` executing atomic PostgreSQL `TRUNCATE TABLE ... CASCADE` across all 15 relational tables
- [x] T031 [US6] Implement maintenance endpoints `DELETE /api/database` and `POST /api/database/clear` in `backend/app/api/database.py` with safety guard checking `SimulationManager.has_active_simulations()` (returning HTTP 409 if active) and returning `PurgeDatabaseResponse`
- [x] T032 [US6] Mount database maintenance router in `backend/app/api/router.py` and verify all tests pass in `backend/tests/test_api_database.py`

**Checkpoint**: Database maintenance and storage reset endpoints fully functional and guarded.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end integration, performance validation, and documentation

- [x] T033 [P] Update API documentation, tags, and OpenAPI metadata in `backend/app/main.py`
- [x] T034 [P] Validate all 6 scenarios in `specs/007-simulation-frontend-api/quickstart.md`
- [x] T035 Execute full pytest test suite across `backend/tests/test_api_*.py` and verify zero regressions across existing 176 tests

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 completion - BLOCKS all user stories.
- **User Story 1 (Phase 3)**: Depends on Phase 2 completion. Delivers the MVP.
- **User Story 2 (Phase 4)**: Depends on Phase 2 and integrates with US1 session provisioning.
- **User Story 3 (Phase 5)**: Depends on Phase 3 and Phase 4 (controls live streaming sessions).
- **User Story 4 (Phase 6)**: Depends on Phase 2 (persistence models and repository).
- **User Story 5 (Phase 7)**: Depends on Phase 2 (persistence repository and catalog queries).
- **User Story 6 (Phase 8)**: Depends on Phase 2 (persistence repository and `SimulationManager` active check).
- **Polish (Phase 9)**: Depends on completion of all desired user stories.

### Parallel Opportunities

- **Phase 2 (Foundational)**: T003 (`schemas.py`) and T004 (`test_api_schemas.py`) can proceed in parallel.
- **Phase 3 (User Story 1)**: T007 (`test_api_simulations.py`) can be authored in parallel with T008 (`provider factory`).
- **Phase 4 (User Story 2)**: T011 (`test_api_websocket.py`) and T012 (`deviation schemas`) can proceed in parallel.
- **Phase 5 (User Story 3)**: T017 (`flow control tests`) can be authored while T018 (`websocket commands`) is drafted.
- **Phase 6 (User Story 4)**: T021 (`export tests`) can be authored in parallel with T022 (`RunExporter streaming`).
- **Phase 7 (User Story 5)**: T026 (`catalog tests`) can be authored in parallel with repository queries.
- **Phase 8 (User Story 6)**: T029 (`purge tests`) can be authored in parallel with T030 (`purge repository method`).
- **User Stories 4, 5, 6**: Once Phase 2 is complete, User Story 4 (Export), User Story 5 (Catalog), and User Story 6 (Purge) can be developed in parallel by separate developers alongside User Story 2 & 3.

---

## Parallel Example: User Story 2 (Real-Time Telemetry & Strategy Deviations)

```bash
# Author tests and data models concurrently:
Task T011: "Create WebSocket connection and telemetry streaming tests in backend/tests/test_api_websocket.py"
Task T012: "Implement strategy deviation schemas and tracker models in backend/app/api/schemas.py"

# Once models and tests are defined:
Task T013: "Implement background simulation execution loop and telemetry bridge in backend/app/api/manager.py"
Task T014: "Implement native FastAPI WebSocket endpoint /ws/simulations/{session_id} in backend/app/api/websocket.py"
Task T015: "Implement dedicated analytics endpoint GET /api/simulations/{session_id}/deviations in backend/app/api/simulations.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete **Phase 1: Setup** (T001 - T002)
2. Complete **Phase 2: Foundational** (T003 - T006)
3. Complete **Phase 3: User Story 1** (T007 - T010)
4. **STOP and VALIDATE**: Verify `POST /api/simulations` provisions tables with identical shoes and returns session metadata via `pytest backend/tests/test_api_simulations.py`.

### Incremental Delivery

1. **Increment 1 (MVP)**: Setup + Foundation + User Story 1 → Clients can configure rules and initialize sessions.
2. **Increment 2**: User Story 2 → Live WebSocket streaming + real-time Basic Strategy deviation analytics.
3. **Increment 3**: User Story 3 → Flow control (`pause`, `resume`, `step`, `stop`, `set_speed`, `retry`).
4. **Increment 4**: User Story 4 → Single-run and full-database JSON downloads.
5. **Increment 5**: User Story 5 → Historical runs browsing and detailed performance metrics.
6. **Increment 6**: User Story 6 → Database purge and reset button backend.
7. **Increment 7**: Polish & Cross-Cutting Concerns → End-to-end quickstart validation and regression suite.
