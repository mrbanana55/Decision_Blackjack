# Tasks: Full Basic Strategy Player & Decision Comparison Oracle

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)  
**Package**: `backend/app/models/` & `backend/app/simulation/`  
**Date**: 2026-10-11  

---

## Phase 1: Setup (Shared Infrastructure & Model Architecture)

**Purpose**: Initialize the core model files inside `backend/app/models/`, declare evaluation schemas, and extend public protocols.

- [x] T001 Initialize package structure in `backend/app/models/` with public export declarations in `backend/app/models/__init__.py`
- [x] T002 [P] Implement decision comparison domain models (`DecisionCategory`, `DecisionComparison`, `BetComparison`, `BetSpreadConfig`) in `backend/app/models/decision_comparator.py`
- [x] T003 [P] Extend `DecisionProvider` protocol in `backend/app/simulation/interfaces.py` with optional `get_bet(bankroll: float, min_bet: float) -> float` and `reset_count() -> None`

---

## Phase 2: Foundational (Matrix Tables & Card Counting Engine)

**Purpose**: Implement the game-theoretic matrix lookup tables and Hi-Lo card counting tracker that underpin both the autonomous player and the comparison oracle.

**⚠️ CRITICAL**: Must be implemented and thoroughly verified before completing user stories.

- [x] T004 [P] Create unit tests in `backend/tests/test_strategy_matrices.py` verifying 100% cell coverage across all 4 charts from `docs/Estrategia Optima.md` (Hard totals, Soft totals, Pairs with DAS, Surrender, and Insurance rejection)
- [x] T005 Implement complete strategy lookup tables (`HARD_TOTALS_MATRIX`, `SOFT_TOTALS_MATRIX`, `PAIR_SPLITTING_MATRIX`, `SURRENDER_MATRIX`, `get_optimal_action()`) in `backend/app/models/strategy_matrices.py`
- [x] T006 [P] Create unit tests in `backend/tests/test_card_counter.py` verifying Hi-Lo card weighting, running count tracking, remaining deck estimation, true count calculation, and count reset
- [x] T007 Implement `HiLoCardCounter` with deck estimation, True Count calculation, and reset triggers in `backend/app/models/card_counter.py`

**Checkpoint**: Core mathematical models, chart lookups, and card counter are verified with automated unit tests.

---

## Phase 3: User Story 1 - Full Optimal Strategy Table Decision Execution (Priority: P1) 🎯 MVP

**Goal**: Deliver a 100% compliant `BasicStrategyPlayer` in `backend/app/models/basic_strategy_player.py` executing optimal game theory decisions across all hand combinations without guessing or heuristics.

**Independent Test**: Can be tested independently by querying the player against arbitrary hand states and dealer upcards across all 4 matrix categories, verifying 100% exact action matching and proper fallback handling (`D` $\rightarrow$ `HIT`, `Ds` $\rightarrow$ `STAND`).

### Tests for User Story 1 ⚠️

- [x] T008 [P] [US1] Create unit tests in `backend/tests/test_basic_strategy_player.py` verifying player decisions across hard totals, soft totals, pair splitting (DAS and no-DAS), surrender, and insurance decline

### Implementation for User Story 1

- [x] T009 [US1] Implement `BasicStrategyPlayer` conforming to `DecisionProvider` with `get_decision(context)` executing strict matrix lookup in `backend/app/models/basic_strategy_player.py`
- [x] T010 [US1] Implement doubling fallback rules (`D` fallback to `HIT`, `Ds` fallback to `STAND`) when doubling is illegal in `backend/app/models/basic_strategy_player.py`
- [x] T011 [US1] Ensure `BasicStrategyPlayer` declines insurance under all circumstances in `backend/app/models/basic_strategy_player.py`

**Checkpoint**: User Story 1 is functional! The Basic Strategy player makes zero-guess, 100% mathematically optimal decisions.

---

## Phase 4: User Story 2 - Dynamic True Count Bet Sizing (Priority: P1)

**Goal**: Enable the Basic Strategy Player to compute optimal initial round wagers based on observed True Count (TC) and table minimum bet ($TC \leq 0 \rightarrow 1 \times \text{min\_bet}$, $TC > 0 \rightarrow N \times \text{min\_bet}$ up to max spread).

**Independent Test**: Can be tested independently by supplying varied card sequences to update internal count and invoking `get_bet()`, verifying that bet sizes scale with True Count and respect available bankroll.

### Tests for User Story 2 ⚠️

- [x] T012 [P] [US2] Create bet sizing unit tests in `backend/tests/test_basic_strategy_betting.py` verifying minimum bets at $TC \leq 0$, proportional sizing at $TC > 0$, bet spread clamping, and bankroll boundaries

### Implementation for User Story 2

- [x] T013 [US2] Implement `get_bet(bankroll, min_bet)` in `BasicStrategyPlayer` inside `backend/app/models/basic_strategy_player.py` calculating wagers based on `BetSpreadConfig` and `HiLoCardCounter`
- [x] T014 [US2] Implement card observation methods (`observe_card`, `observe_cards`) and `reset_count()` in `backend/app/models/basic_strategy_player.py`

**Checkpoint**: User Stories 1 and 2 operate together as a full-featured card-counting advantage player.

---

## Phase 5: User Story 3 - Decision & Bet Comparison Evaluation Oracle (Priority: P2)

**Goal**: Implement the standalone `DecisionComparator` evaluation oracle in `backend/app/models/decision_comparator.py` to compare any other agent's decisions (Jev or Laya) and opening bets against what Basic Strategy would dictate in that agent's exact table position.

**Independent Test**: Can be tested independently by evaluating arbitrary external agent decisions (e.g. Jev hitting on 15 vs 2 while Basic Strategy plays 12 vs 5) and wagers, verifying that optimal action/bet, delta, and deviation explanations are generated cleanly.

### Tests for User Story 3 ⚠️

- [x] T015 [P] [US3] Create unit tests in `backend/tests/test_decision_comparator.py` verifying positional hand evaluations, bet spread comparisons, optimality flags, and category classification

### Implementation for User Story 3

- [x] T016 [US3] Implement `evaluate_turn_decision(context, actual_action)` in `backend/app/models/decision_comparator.py` evaluating the optimal action for that specific position and returning `DecisionComparison`
- [x] T017 [US3] Implement `evaluate_round_bet(actual_bet, min_bet, true_count, bankroll)` in `backend/app/models/decision_comparator.py` returning `BetComparison`
- [x] T018 [US3] Wire inline decision comparison into `EntityTable.play_turn()` in `backend/app/simulation/table.py` and attach `comparison` metadata to `AgentDecision` and `SimulationMetrics`

**Checkpoint**: The evaluation oracle can benchmark any player's moves and bets against game-theoretic optimality in real-time.

---

## Phase 6: User Story 4 - Seamless Orchestrator Integration & Replacement (Priority: P2)

**Goal**: Replace the mockup basic strategy player with the new implementation across orchestrator tables, wire `get_bet()` and `reset_count()` into the simulation lifecycle, and ensure zero test regressions.

**Independent Test**: Can be tested independently by running all existing orchestrator test suites (`backend/tests/test_simulation_*.py`), verifying 100% pass rate.

### Tests for User Story 4 ⚠️

- [x] T019 [P] [US4] Verify orchestrator multi-agent tests in `backend/tests/test_simulation_orchestrator.py` and `backend/tests/test_simulation_quickstart.py` with the updated player

### Implementation for User Story 4

- [x] T020 [US4] Replace mockup player in `backend/app/simulation/agents/basic_strategy.py` by re-exporting `BasicStrategyPlayer` from `app.models` as `BasicStrategyAgent`
- [x] T021 [US4] Update `EntityTable.start_round()` in `backend/app/simulation/table.py` to query `provider.get_bet()` when available
- [x] T022 [US4] Update `EntityTable.adopt_shoe()` and round reshuffle handling in `backend/app/simulation/table.py` to invoke `provider.reset_count()` when supported
- [x] T023 [US4] Update `SimulationOrchestrator` in `backend/app/simulation/orchestrator.py` to forward card deal events and attach comparison telemetry to `DECISION_APPLIED`

**Checkpoint**: The new player is fully integrated into the orchestrator and all existing tests pass without regressions.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validate quickstart scenarios, run static analysis and linting, and update project documentation.

- [x] T024 [P] Validate all scenarios from `specs/003-basic-strategy-player/quickstart.md` in `backend/tests/test_basic_strategy_quickstart.py`
- [x] T025 [P] Run linter and formatting checks via `ruff check backend/app/models backend/app/simulation`
- [x] T026 Execute complete project test suite verifying 100% test pass rate across engine, simulation, and models via `pytest backend/tests/ -v`
- [x] T027 Update `docs/Estrategia Optima.md` and `docs/session_logs.md` documenting deliverables and API reference

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Can begin immediately.
- **Foundational (Phase 2)**: Depends on Setup (T001–T003) - BLOCKS all User Stories.
- **User Story 1 (Phase 3)**: Depends on Foundational completion (T004–T007). Delivers MVP.
- **User Story 2 (Phase 4)**: Depends on US1 (T009) and Card Counter (T007).
- **User Story 3 (Phase 5)**: Depends on US1 & US2 completion (T009, T013).
- **User Story 4 (Phase 6)**: Depends on US1, US2, and US3 completion (T009, T013, T016–T018).
- **Polish (Phase 7)**: Depends on all user stories being completed.

### Parallel Opportunities

- **Phase 1**: T002 (`decision_comparator.py` schemas) and T003 (`interfaces.py` protocol extensions) can run in parallel.
- **Phase 2**: T004/T005 (Strategy matrices) and T006/T007 (Card counter) can run in parallel.
- **Phase 3**: T008 (Player tests) can be written in parallel with T005.
- **Phase 4**: T012 (Betting tests) can run in parallel with US1 tasks.
- **Phase 5**: T015 (Comparator tests) can run in parallel with earlier tasks.
- **Phase 7**: T024 (`test_basic_strategy_quickstart.py`) and T025 (`ruff check`) can run in parallel.

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Complete Phase 1 (Setup: models directory and schemas).
2. Complete Phase 2 (Foundational: matrix lookups and Hi-Lo card counter).
3. Complete Phase 3 (User Story 1: `BasicStrategyPlayer` executing strict matrix decisions).
4. **STOP and VALIDATE**: Verify that every hand combination produces the exact expected basic strategy action.

### Incremental Delivery
1. Add Phase 4 (User Story 2: True Count card counting bet spread sizing).
2. Add Phase 5 (User Story 3: Contextual positional decision & bet comparison oracle).
3. Add Phase 6 (User Story 4: Seamless orchestrator replacement and telemetry integration).
4. Run Phase 7 (Polish: quickstart tests, linting, regression verification).
