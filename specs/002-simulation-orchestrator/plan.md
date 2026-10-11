# Implementation Plan: Simulation Orchestrator

**Branch**: `002-simulation-orchestrator` | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-simulation-orchestrator/spec.md`

---

## Summary

Build the `SimulationOrchestrator` in `backend/app/simulation/` to manage multi-agent Blackjack simulations across isolated entity tables (Jev, Laya, and Optimal Strategy) under identical initial conditions. The orchestrator coordinates concurrent round execution with synchronous round barriers, manages generational shoe pools across desynchronized tables, enforces fail-fast error recovery, provides pause/resume/step controls, and broadcasts structured telemetry events.

Per user instruction, temporary fake agents (`FakeJevAgent`, `FakeLayaAgent`) and a baseline `BasicStrategyAgent` are isolated inside `backend/app/simulation/agents/` behind a clean `DecisionProvider` protocol so they can be seamlessly swapped for real agent implementations in future specs without modifying the orchestrator core.

---

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: Standard library (`asyncio`, `dataclasses`, `uuid`, `enum`, `typing`), `numpy>=2.0.0`, internal core engine package (`app.engine.*`)  
**Storage**: In-memory state and event history (structured database persistence in later specs)  
**Testing**: `pytest`, `pytest-asyncio` via `uv` or Docker compose / native Python test runner  
**Target Platform**: Linux / macOS containerized development & server environment  
**Project Type**: Core domain service / simulation orchestrator  
**Performance Goals**: 100 synchronized 3-entity rounds in under 2 seconds; zero CPU spinning when paused  
**Constraints**: Zero UI or HTTP dependencies; headless execution with fake agents; fail-fast pause upon provider faults (RNF-02)  
**Scale/Scope**: Up to 10,000 continuous rounds per simulation run; support for 3 concurrent entity tables  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Principle I: Engine Independence & Determinism**  
  *Status: PASS*. The orchestrator in `backend/app/simulation/` consumes `backend/app/engine/` as a pure, deterministic dependency without mutating or re-implementing core rules.
- [x] **Principle II: Tri-Entity Synchronization & Experiment Isolation**  
  *Status: PASS*. Each entity (Jev, Laya, Optimal Strategy) plays an independent table instance initialized from the identical root seed and table rules. A synchronous round barrier ensures round parity before advancing to round $N+1$.
- [x] **Principle III: Provider Abstraction & Model Decoupling**  
  *Status: PASS*. All agents implement the abstract `DecisionProvider` protocol. Fake agents are isolated in `app/simulation/agents/fake_agents.py`, easily removable when real model adapters are introduced. Transient errors trigger a graceful pause in `PAUSED_ERROR` state.
- [x] **Principle IV: Seeded Reproducibility**  
  *Status: PASS*. Multi-table sessions share a deterministic `ShoePool` generating numbered shoe generations (`seed + generation * 1000`) so tables consume identical shoes even when player actions deplete cards at varying rates.
- [x] **Principle V: Telemetry, Structured Persistence & Batch Safety**  
  *Status: PASS*. Strongly typed event broadcasting (`EventEmitter`) publishes all session, round, turn, card, and decision events without coupling execution to persistence backends.

---

## Project Structure

### Documentation (this feature)

```text
specs/002-simulation-orchestrator/
├── spec.md              # Feature specification & clarifications
├── plan.md              # Implementation plan (this document)
├── research.md          # Phase 0 architectural & technical decisions
├── data-model.md        # Phase 1 class diagram, entities & state transitions
├── contracts/           # Phase 1 API specifications
│   └── orchestrator_api.md
├── quickstart.md        # Phase 1 runnable validation scenarios
└── checklists/
    └── requirements.md  # Quality assurance checklist
```

### Source Code (`backend/`)

```text
backend/app/simulation/
├── __init__.py           # Public exports (SimulationOrchestrator, ShoePool, DecisionProvider, events)
├── types.py              # Enums (SessionStatus, EntityType) and dataclasses (SimulationConfig, DecisionContext, AgentDecision)
├── interfaces.py         # Protocols (DecisionProvider, OrchestratorController, EventPublisher) and domain exceptions
├── events.py             # EventType enum, SimulationEvent hierarchy, and EventEmitter bus
├── shoe_pool.py          # ShoePool generational shoe cache across desynchronized tables
├── table.py              # EntityTable isolated game table wrapper managing turns & metrics
├── orchestrator.py       # SimulationOrchestrator coordinating rounds, barriers, pause/resume, and error handling
└── agents/               # Isolated agent implementations
    ├── __init__.py       # Agent exports
    ├── basic_strategy.py # Mathematical Basic Strategy baseline provider
    └── fake_agents.py    # Temporary FakeJevAgent and FakeLayaAgent (mock latency & fault injection)

backend/tests/
├── test_simulation_shoe_pool.py       # Generational shoe caching and determinism
├── test_simulation_agents.py          # Fake agents, basic strategy, and latency/fault simulation
├── test_simulation_table.py           # EntityTable turn mechanics and metrics tracking
├── test_simulation_events.py          # Event bus broadcasting and chronological order
├── test_simulation_orchestrator.py    # Lifecycle, round barrier, pause/resume/step, and fail-fast recovery
└── test_simulation_quickstart.py      # Quickstart scenarios validation
```

**Structure Decision**:
- All orchestrator domain logic lives strictly inside `backend/app/simulation/`.
- Temporary fake agents are isolated in `backend/app/simulation/agents/fake_agents.py` behind the `DecisionProvider` protocol. They can be removed or supplemented in future specs with zero impact on orchestrator core code.
- Core Blackjack engine (`backend/app/engine/`) remains completely untouched as an immutable, independent library.

---

## Complexity Tracking

*No constitutional violations identified. No unjustified architectural complexity.*
