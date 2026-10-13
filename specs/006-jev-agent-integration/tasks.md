# Tasks: Jev Decision Agent Integration & Remote System One Provider

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)  
**Package**: `backend/app/integrations/jev/`  
**Date**: 2026-10-12  

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Package initialization, dynamic environment configuration, and exports wiring.

- [x] T001 Initialize package structure in `backend/app/integrations/jev/__init__.py` with public export declarations (`JevAgent`, `JevClient`, `JevConfig`, `JevSchemaBuilder`).
- [x] T002 [P] Implement `JevConfig` in `backend/app/integrations/jev/config.py` loading `TYPESAFE_API_KEY`, `TYPESAFE_API_URL` (default `https://api.typesafe.ai/v1/systemone`), `TYPESAFE_MODEL` (default `jev-latest`), `timeout_seconds` (default 15.0), `connect_timeout_seconds` (default 3.0), and `max_retries` (default 3) from `.env`.
- [x] T003 [P] Register Jev exports in `backend/app/integrations/__init__.py` exposing `JevAgent`, `JevClient`, `JevConfig`, and `JevSchemaBuilder` alongside Laya exports.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core TypeSafe System One Pydantic v2 schemas and async HTTP client infrastructure with Bearer authentication and rate-limit backoff.

**⚠️ CRITICAL**: All user stories depend on these transport models, authentication headers, and client connection abstractions.

- [x] T004 [P] Implement TypeSafe System One models (`QuestionType`, `ChoiceQuestion`, `SystemOneRequest`, `ChoiceAnswer`, `UsageInfo`, `SystemOneResponse`, `JevHealthStatus`, `HandSituationType`) conforming to TypeSafe System One API specification in `backend/app/integrations/jev/schemas.py`.
- [x] T005 [P] Implement `JevClient` in `backend/app/integrations/jev/client.py` using `httpx.AsyncClient` with Bearer authorization (`Authorization: Bearer <TYPESAFE_API_KEY>`), request dispatch (`POST /v1/systemone`), high-precision latency measurement, exponential backoff retries on HTTP 429 and 529, and error translation raising `AgentFaultError`.

**Checkpoint**: Foundation ready — transport schemas and async HTTP client exist and are ready for agent integration.

---

## Phase 3: User Story 1 - Real-Time Hand Action Decisions via Remote Jev Model (Priority: P1) 🎯 MVP

**Goal**: Deliver autonomous in-hand playing decisions (Hit, Stand, Double, Split, Surrender) for Jev, dynamically constructing question criteria matching table rules and player state.

**Independent Test**: Can be tested independently by creating a simulation session with `JevAgent`, stepping through active player turns, and verifying that discrete actions returned by Jev are executed without illegal action errors.

### Tests for User Story 1 ⚠️

- [x] T006 [P] [US1] Create unit tests in `backend/tests/test_jev_schemas.py` validating dynamic situational schema construction for Initial Paired Hand (Contract 1A/1B), Initial Standard Hand (Contract 2A/2B), and Multi-Card Draw Hand (Contract 3) respecting `legal_actions` and table rules.
- [x] T007 [P] [US1] Create unit tests in `backend/tests/test_jev_agent.py` testing `JevAgent.get_decision()` with mock and live responses, validating action mapping (`hit`, `stand`, `double`, `split`, `surrender` $\to$ `Action`), confidence extraction, latency timing, probability distribution, token usage, and metadata packaging.

### Implementation for User Story 1

- [x] T008 [US1] Implement `JevSchemaBuilder` in `backend/app/integrations/jev/builder.py` with `build_hand_decision_request(context: DecisionContext, rules: TableRules)` dynamically generating natural language `state` with `model="jev-latest"` and filtering `criteria` options strictly from `context.legal_actions`.
- [x] T009 [US1] Implement `JevAgent` in `backend/app/integrations/jev/agent.py` satisfying `DecisionProvider` protocol (`name="Jev"`, `entity_type=EntityType.JEV`, `get_decision(context: DecisionContext) -> AgentDecision`).
- [x] T010 [US1] Register `JevAgent` in `backend/app/simulation/__init__.py` and `backend/app/simulation/agents/__init__.py` so simulation orchestrators and entity factories resolve real `JevAgent` instances alongside `LayaAgent` and `BasicStrategyPlayer`.

**Checkpoint**: User Story 1 complete! Jev autonomously evaluates active hands and plays valid moves during simulation turns.

---

## Phase 4: User Story 2 - Remote Provider Authentication, Configuration & Health Probes (Priority: P1)

**Goal**: Verify seamless authentication against TypeSafe System One using `.env` credentials and expose a diagnostic health check endpoint (`/health`).

**Independent Test**: Can be tested independently by running health probes against `/health` and verifying status, model alias, and key presence.

### Tests for User Story 2 ⚠️

- [x] T011 [P] [US2] Create unit tests in `backend/tests/test_jev_config.py` verifying `TYPESAFE_API_KEY`, `TYPESAFE_API_URL`, and `TYPESAFE_MODEL` parsing from `.env`, default fallbacks, and validation on empty keys.
- [x] T012 [P] [US2] Create integration tests in `backend/tests/test_jev_client.py` testing `JevClient.check_health()` probing `/health` and handling connection failures gracefully.

### Implementation for User Story 2

- [x] T013 [US2] Implement health check verification method `check_health()` in `backend/app/integrations/jev/client.py` probing `/health`.

**Checkpoint**: User Story 2 complete! Backend service verifies credentials and reachability via `/health`.

---

## Phase 5: User Story 3 - Multi-Phase Game Decisions: Discrete Bet Sizing & Insurance (Priority: P2)

**Goal**: Consult Jev during pre-deal round wagering (`1x`, `2x`, `4x`, `8x` of dynamic table minimum bet) and insurance offers (when dealer reveals an Ace).

**Independent Test**: Can be tested independently by running rounds with dealer Aces and verifying that Jev selects discrete wagers and resolves insurance choices via TypeSafe Choice questions.

### Tests for User Story 3 ⚠️

- [x] T014 [P] [US3] Create unit tests in `backend/tests/test_jev_schemas.py` validating Situation 4 (Insurance Offer Contract) and Situation 5 (Round Betting Contract with dynamic `TableRules.min_bet`, scaling `1x`, `2x`, `4x`, `8x`).
- [x] T015 [P] [US3] Create unit tests in `backend/tests/test_jev_agent.py` testing `JevAgent.get_bet()` and `JevAgent.get_insurance()` parsing choice answers into concrete currency amounts and boolean decisions.

### Implementation for User Story 3

- [x] T016 [US3] Implement `build_betting_request()` and `build_insurance_request()` in `backend/app/integrations/jev/builder.py` formatting discrete bet multipliers (`1x`, `2x`, `4x`, `8x` of dynamic `rules.min_bet`) and insurance choices (`accept` vs `decline`).
- [x] T017 [US3] Implement `get_bet(bankroll: float, min_bet: float, true_count: float)` and `get_insurance(context: DecisionContext, insurance_cost: float) -> bool` on `JevAgent` in `backend/app/integrations/jev/agent.py`.
- [x] T018 [US3] Connect `JevAgent` betting and insurance methods into `EntityTable` in `backend/app/simulation/table.py` for `EntityType.JEV`, ensuring `get_bet()` runs before deals and `get_insurance()` during insurance offers.

**Checkpoint**: User Story 3 complete! Jev autonomously sizes round bets and evaluates insurance offers.

---

## Phase 6: User Story 4 - Fault Resilience, Rate Limiting & Comparative Telemetry (Priority: P2)

**Goal**: Guarantee RNF-02 fault pause compliance on rate limit exhaustion or network drops, preserve telemetry in PostgreSQL persistence (`decisions` and `model_responses`), and cross-evaluate Jev choices against Basic Strategy.

**Independent Test**: Can be tested independently by injecting rate limit (HTTP 429) exhaustion or network timeouts during active multi-agent simulation rounds, verifying synchronous pause with state preservation, and inspecting comparator metrics in database records.

### Tests for User Story 4 ⚠️

- [x] T019 [P] [US4] Create simulation integration tests in `backend/tests/test_jev_simulation.py` asserting that Jev timeouts, rate limit exhaustion, or network drops trigger `AgentFaultError`, pause all synchronized tables in `PAUSED_ERROR` without data loss, and allow resume.

### Implementation for User Story 4

- [x] T020 [US4] Attach Jev inference telemetry (model name, token usage, latency, probabilities, confidence, raw request/response) to orchestrator events and persist to `Decision` and `ModelResponse` tables (`provider=ModelProvider.SYSTEM_ONE`) in `backend/app/persistence/listener.py`.
- [x] T021 [US4] Wire real-time `DecisionComparator` evaluation for Jev decisions in `backend/app/simulation/orchestrator.py` recording agreement with optimal basic strategy and calculating expected value deviations.

**Checkpoint**: User Story 4 complete! System pauses gracefully on API faults, preserves telemetry, and benchmarks Jev against game theory.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validation, linter verification, documentation, and regression safety.

- [x] T022 [P] Execute quickstart verification workflow from `specs/006-jev-agent-integration/quickstart.md` inside Docker container (`docker compose exec backend uv run pytest tests/test_jev_*.py`).
- [x] T023 [P] Run code formatting and linting checks across all new modules and tests via `docker compose exec backend uv run ruff check app/integrations/jev tests/test_jev_*.py`.
- [x] T024 Document Jev integration configuration, architecture, and verification results in `docs/session_logs.md`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories.
- **User Stories (Phase 3+)**: Depend on Foundational phase completion.
  - User Story 1 (P1): Core MVP — hand play decisions.
  - User Story 2 (P1): Authentication & health checks.
  - User Story 3 (P2): Multi-phase betting & insurance decisions.
  - User Story 4 (P2): Fault recovery, rate limiting, persistence telemetry, and comparator evaluation.
- **Polish (Phase 7)**: Depends on all user stories being completed.

### Parallel Opportunities

- Within Phase 1: `T002` (config) and `T003` (exports) can run in parallel.
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
4. **VALIDATE MVP**: Run `docker compose exec backend uv run pytest tests/test_jev_schemas.py tests/test_jev_agent.py`.
5. Verify in-hand playing decisions execute cleanly.

### Incremental Delivery
1. Add User Story 2 (`T011`–`T013`): Verify health check probe and credential validation.
2. Add User Story 3 (`T014`–`T018`): Enable dynamic bet sizing and insurance choices.
3. Add User Story 4 (`T019`–`T021`): Enable RNF-02 fault pause, rate-limiting backoff, and comparator telemetry.
4. Final Polish (`T022`–`T024`): Run full quickstart suite, linting, and session logs documentation.
