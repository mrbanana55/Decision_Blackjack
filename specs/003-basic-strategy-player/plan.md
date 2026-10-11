# Implementation Plan: Full Basic Strategy Player & Decision Comparison Oracle

**Branch**: `003-basic-strategy-player` | **Date**: 2026-10-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-basic-strategy-player/spec.md` and user directive: `Create this inside @[backend/app/models]`.

---

## Summary

Implement the complete, deterministic Blackjack Basic Strategy player strictly based on the game-theory matrices in `docs/Estrategia Optima.md` along with a standalone contextual **Decision Comparison Oracle** (`DecisionComparator`).

Per user instructions, all core strategy models, lookup matrices, card counting utilities, and comparison models will be created inside `backend/app/models/`. The existing mockup `BasicStrategyAgent` in `backend/app/simulation/agents/basic_strategy.py` will be cleanly replaced with the new implementation to ensure 100% backward compatibility. The orchestrator and table will be updated to query `get_bet()`, invoke `reset_count()`, and inline `DecisionComparison` telemetry events.

---

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: Standard library (`dataclasses`, `enum`, `typing`, `math`), `numpy>=2.0.0`, internal core engine package (`app.engine.*`), simulation types (`app.simulation.types.*`)  
**Storage**: Pure in-memory (telemetry events prepared for database persistence in future specs)  
**Testing**: `pytest`, `pytest-asyncio` via `uv` or native Python runner  
**Target Platform**: Linux / macOS containerized development & server environment  
**Project Type**: Core domain models, strategy engine, and evaluation service  
**Performance Goals**: Turn decision execution under 0.1 ms; comparison evaluation under 0.05 ms  
**Constraints**: Zero guesses/heuristics; 100% adherence to `docs/Estrategia Optima.md`; zero network/UI dependencies  
**Scale/Scope**: 100% matrix coverage (Hard, Soft, Pairs with DAS, Surrender, Insurance rejection, Hi-Lo Bet Spread)  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Principle I: Engine Independence & Determinism**  
  *Status: PASS*. The models in `backend/app/models/` consume `backend/app/engine/` as pure data primitives (`Card`, `Rank`, `Action`, `TableRules`) without modifying the deterministic core engine.
- [x] **Principle II: Tri-Entity Synchronization & Experiment Isolation**  
  *Status: PASS*. The Basic Strategy player plays its own table independently. Meanwhile, the `DecisionComparator` evaluates other agents (Jev, Laya) strictly in their respective table positions without cross-table state contamination.
- [x] **Principle III: Provider Abstraction & Model Decoupling**  
  *Status: PASS*. `BasicStrategyPlayer` implements the `DecisionProvider` protocol. The models have zero HTTP or vendor SDK dependencies.
- [x] **Principle IV: Seeded Reproducibility**  
  *Status: PASS*. All strategy lookups and Hi-Lo card counting math are 100% deterministic functions of observed cards and rules.
- [x] **Principle V: Telemetry, Structured Persistence & Batch Safety**  
  *Status: PASS*. Telemetry events emit structured `DecisionComparison` and `BetComparison` payloads for persistence and UI streaming.

---

## Project Structure

### Documentation (`specs/003-basic-strategy-player/`)

```text
specs/003-basic-strategy-player/
├── spec.md                  # Feature specification & clarifications
├── plan.md                  # Implementation plan (this document)
├── research.md              # Phase 0 architectural & technical decisions
├── data-model.md            # Phase 1 data models & class diagrams
├── contracts/               # Phase 1 interface contracts
│   └── basic_strategy_api.md
├── quickstart.md            # Phase 1 validation scenarios
└── checklists/
    └── requirements.md      # Specification quality checklist
```

### Source Code (`backend/`)

```text
backend/app/models/
├── __init__.py               # Exports StrategyMatrix, CardCounter, DecisionComparator, BasicStrategyPlayer
├── strategy_matrices.py      # Hard, Soft, Pair (DAS-aware), Surrender lookup matrices (from docs/Estrategia Optima.md)
├── card_counter.py           # Hi-Lo running and true count tracker (HiLoCardCounter)
├── decision_comparator.py    # Standalone contextual Decision & Bet Comparison Oracle (DecisionComparator)
└── basic_strategy_player.py  # Concrete DecisionProvider implementation using matrices & Hi-Lo counting

backend/app/simulation/
├── interfaces.py             # Extended DecisionProvider protocol with optional get_bet & reset_count
├── table.py                  # Updated EntityTable to call get_bet(), reset_count(), and track comparisons
├── orchestrator.py           # Updated to emit comparison payloads in DECISION_APPLIED and ROUND_STARTED
└── agents/
    └── basic_strategy.py     # Backward-compatible proxy to BasicStrategyPlayer in app.models

backend/tests/
├── test_strategy_matrices.py      # 100% cell coverage tests across all 4 strategy charts
├── test_card_counter.py           # Hi-Lo count tracking, True Count calculation, and deck estimation
├── test_decision_comparator.py    # Positional decision comparison and bet comparison verification
├── test_basic_strategy_player.py  # End-to-end player decisions, get_bet, and reset_count
└── test_simulation_*.py           # Verification that all 76 existing tests continue to pass (zero regressions)
```

**Structure Decision**:
- All core game theory logic, lookup matrices, card counting, and evaluation oracles reside in `backend/app/models/` as requested.
- `backend/app/simulation/agents/basic_strategy.py` simply re-exports `BasicStrategyPlayer` as `BasicStrategyAgent` to guarantee zero breaking changes across existing code.

---

## Complexity Tracking

*No constitutional violations identified. Design cleanly separates models from orchestration.*
