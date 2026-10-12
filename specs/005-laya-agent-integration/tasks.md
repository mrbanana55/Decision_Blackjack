# Tasks: Laya Decision Agent Integration & Container Host Bridge

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)  
**Package**: `backend/app/integrations/laya/`  
**Date**: 2026-10-11  

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Package initialization, dynamic environment configuration, and Docker host-bridge routing.

- [x] T001 Initialize package structure in `backend/app/integrations/laya/__init__.py` with public export declarations (`LayaAgent`, `LayaClient`, `LayaConfig`, `LayaSchemaBuilder`).
- [x] T002 [P] Implement `LayaConfig` in `backend/app/integrations/laya/config.py` loading `LAYA_BASE_URL` from `.env`, supporting custom host ports, and automatically normalizing `127.0.0.1`/`localhost` to `host.docker.internal` inside Docker environments.
- [x] T003 [P] Configure host gateway routing in `docker-compose.yml` by adding `extra_hosts: ["host.docker.internal:host-gateway"]` and environment variable `LAYA_BASE_URL: ${LAYA_BASE_URL:-http://host.docker.internal:1234}` to the `backend` service.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core TypeSafe System One Pydantic v2 schemas and async HTTP client infrastructure.

**⚠️ CRITICAL**: All user stories depend on these transport models and client connection abstractions.

- [x] T004 [P] Implement TypeSafe System One models (`QuestionType`, `ChoiceQuestion`, `SystemOneRequest`, `ChoiceAnswer`, `SystemOneResponse`, `LayaHealthStatus`, `HandSituationType`) conforming to `docs/Laya_Example_Body.md` in `backend/app/integrations/laya/schemas.py`.
- [x] T005 [P] Implement `LayaClient` using `httpx.AsyncClient` with bounded timeouts (connect: 1.5s, read: 3.0s), health probe (`GET /health`), request dispatch (`POST /v1/systemone`), high-precision latency measurement, and error translation raising `AgentFaultError` in `backend/app/integrations/laya/client.py`.

**Checkpoint**: Foundation ready — transport schemas and async HTTP client exist and are ready for agent integration.

---

## Phase 3: User Story 1 - Real-Time Hand Action Decisions via Local Laya Model (Priority: P1) 🎯 MVP

**Goal**: Deliver autonomous in-hand playing decisions (Hit, Stand, Double, Split, Surrender) for Laya, dynamically constructing question criteria matching table rules and player state.

**Independent Test**: Can be tested independently by creating a simulation session with `LayaAgent`, stepping through active player turns, and verifying that discrete actions returned by Laya are executed without illegal action errors.

### Tests for User Story 1 ⚠️

- [x] T006 [P] [US1] Create unit tests in `backend/tests/test_laya_schemas.py` validating dynamic situational schema construction for Initial Paired Hand (Contract 1A/1B), Initial Standard Hand (Contract 2A/2B), and Multi-Card Draw Hand (Contract 3) respecting `legal_actions` and table rules.
- [x] T007 [P] [US1] Create unit tests in `backend/tests/test_laya_agent.py` testing `LayaAgent.get_decision()` with mock and live responses, validating action mapping (`hit`, `stand`, `double`, `split`, `surrender` $\to$ `Action`), confidence extraction, latency timing, and metadata packaging.

### Implementation for User Story 1

- [x] T008 [US1] Implement `LayaSchemaBuilder` in `backend/app/integrations/laya/builder.py` with `build_hand_decision_request(context: DecisionContext, rules: TableRules)` dynamically generating natural language `state` and filtering `criteria` options strictly from `context.legal_actions`.
- [x] T009 [US1] Implement `LayaAgent` in `backend/app/integrations/laya/agent.py` satisfying `DecisionProvider` protocol (`name="Laya"`, `entity_type=EntityType.LAYA`, `get_decision(context: DecisionContext) -> AgentDecision`).
- [x] T010 [US1] Register `LayaAgent` in `backend/app/simulation/__init__.py` and update simulation orchestrator factory to resolve real `LayaAgent` instances alongside `BasicStrategyAgent`.

**Checkpoint**: User Story 1 complete! Laya autonomously evaluates active hands and plays valid moves during simulation turns.

---

## Phase 4: User Story 2 - Host-Container Network Bridge & Health Connectivity (Priority: P1)

**Goal**: Verify seamless network connectivity between the Docker backend container and host Laya service across any configured port specified in `.env`.

**Independent Test**: Can be tested independently by running health probes against `<LAYA_BASE_URL>/health` from inside the backend container and verifying 200 OK status with device and revision details.

### Tests for User Story 2 ⚠️

- [x] T011 [P] [US2] Create unit tests in `backend/tests/test_laya_config.py` verifying `LAYA_BASE_URL` parsing from `.env`, custom port reconfiguration, and automatic container host normalization (`127.0.0.1` $\to$ `host.docker.internal`).
- [x] T012 [P] [US2] Create integration tests in `backend/tests/test_laya_client.py` testing `LayaClient.check_health()` parsing `/health` payloads (loaded models, revisions, device) and handling connection failures gracefully.

### Implementation for User Story 2

- [x] T013 [US2] Implement health check verification method `check_health()` in `backend/app/integrations/laya/client.py` and register it in the backend FastAPI application health router in `backend/app/main.py`.

**Checkpoint**: User Story 2 complete! Backend container reliably resolves host services across any port configured in `.env`.

---

## Phase 5: User Story 3 - Multi-Phase Game Decisions: Discrete Bet Sizing & Insurance (Priority: P2)

**Goal**: Consult Laya during pre-deal round wagering (`1x`, `2x`, `4x`, `8x` of dynamic table minimum bet) and insurance offers (when dealer reveals an Ace).

**Independent Test**: Can be tested independently by running rounds with dealer Aces and verifying that Laya selects discrete wagers and resolves insurance choices via TypeSafe Choice questions.

### Tests for User Story 3 ⚠️

- [x] T014 [P] [US3] Create unit tests in `backend/tests/test_laya_schemas.py` validating Situation 4 (Insurance Offer Contract) and Situation 5 (Round Betting Contract with dynamic `TableRules.min_bet`, never hardcoded $50).
- [x] T015 [P] [US3] Create unit tests in `backend/tests/test_laya_agent.py` testing `LayaAgent.get_bet()` and `LayaAgent.get_insurance()` parsing choice answers into concrete currency amounts and boolean decisions.

### Implementation for User Story 3

- [x] T016 [US3] Implement `build_betting_request()` and `build_insurance_request()` in `backend/app/integrations/laya/builder.py` formatting discrete bet multipliers (`1x`, `2x`, `4x`, `8x` of dynamic `rules.min_bet`) and insurance choices (`accept` vs `decline`).
- [x] T017 [US3] Implement `get_bet(bankroll: float, min_bet: float, true_count: float)` and `get_insurance(context: DecisionContext, insurance_cost: float) -> bool` on `LayaAgent` in `backend/app/integrations/laya/agent.py`.
- [x] T018 [US3] Connect `LayaAgent` betting and insurance methods into `EntityTable` in `backend/app/simulation/table.py` invoking `get_bet()` before round deal and `get_insurance()` during `INSURANCE_OFFERED` phase.

**Checkpoint**: User Story 3 complete! Laya autonomously sizes round bets and evaluates insurance offers.

---

## Phase 6: User Story 4 - Fault Resilience, Session Preservation & Comparative Analysis (Priority: P2)

**Goal**: Guarantee RNF-02 fault pause compliance on host network disconnects, preserve telemetry in database persistence, and cross-evaluate Laya choices against Basic Strategy.

**Independent Test**: Can be tested independently by injecting network timeouts during active multi-agent simulation rounds, verifying synchronous pause with state preservation, and inspecting comparator metrics in database records.

### Tests for User Story 4 ⚠️

- [x] T019 [P] [US4] Create simulation integration tests in `backend/tests/test_laya_simulation.py` asserting that Laya timeouts or connection drops trigger `AgentFaultError`, pause all synchronized tables without data loss, and allow resume.

### Implementation for User Story 4

- [x] T020 [US4] Attach Laya inference telemetry (model revision, execution device, latency, confidence distribution, raw request/response) to orchestrator events and persist to `Decision` and `ModelResponse` tables in `backend/app/persistence/listener.py`.
- [x] T021 [US4] Wire real-time `DecisionComparator` evaluation for Laya decisions in `backend/app/simulation/orchestrator.py` recording agreement with optimal basic strategy and calculating expected value deviations.

**Checkpoint**: User Story 4 complete! System pauses gracefully on host disconnects, preserves data, and benchmarks Laya against game theory.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validation, linter verification, documentation, and regression safety.

- [x] T022 [P] Execute quickstart verification workflow in `specs/005-laya-agent-integration/quickstart.md` inside Docker container (`docker compose exec backend uv run pytest tests/test_laya_*.py`).
- [x] T023 [P] Run code formatting and linting checks across all new modules and tests via `docker compose exec backend uv run ruff check app/integrations/laya tests/test_laya_*.py`.
- [x] T024 Document Laya integration configuration and usage in `docs/session_logs.md`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories.
- **User Stories (Phase 3+)**: Depend on Foundational phase completion.
  - User Story 1 (P1): Core MVP — hand play decisions.
  - User Story 2 (P1): Network bridge & health checks.
  - User Story 3 (P2): Multi-phase betting & insurance decisions.
  - User Story 4 (P2): Fault recovery, persistence telemetry, and comparator evaluation.
- **Polish (Phase 7)**: Depends on all user stories being completed.

### Parallel Opportunities

- Within Phase 1: `T002` (config) and `T003` (docker-compose) can run in parallel.
- Within Phase 2: `T004` (schemas) and `T005` (client) can run in parallel.
- Within User Story 1: `T006` (schema tests) and `T007` (agent tests) can run in parallel.
- Within User Story 2: `T011` (config tests) and `T012` (client tests) can run in parallel.
- Within User Story 3: `T014` (schema tests) and `T015` (agent tests) can run in parallel.
- Within Polish: `T022` and `T023` can run in parallel.

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Complete Phase 1: Setup (`T001`–`T003`).
2. Complete Phase 2: Foundational (`T004`–`T005`).
3. Complete Phase 3: User Story 1 (`T006`–`T010`).
4. **VALIDATE MVP**: Run `docker compose exec backend uv run pytest tests/test_laya_schemas.py tests/test_laya_agent.py`.
5. Verify in-hand playing decisions execute cleanly.

### Incremental Delivery
1. Add User Story 2 (`T011`–`T013`): Verify health check probe and host routing.
2. Add User Story 3 (`T014`–`T018`): Enable dynamic bet sizing and insurance choices.
3. Add User Story 4 (`T019`–`T021`): Enable RNF-02 fault pause and comparator telemetry.
4. Final Polish (`T022`–`T024`): Run full quickstart suite and linting.
