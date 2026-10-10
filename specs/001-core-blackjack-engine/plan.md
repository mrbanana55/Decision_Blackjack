# Implementation Plan: Core Blackjack Engine

**Branch**: `001-core-blackjack-engine` | **Date**: 2026-10-09 | **Spec**: [specs/001-core-blackjack-engine/spec.md](spec.md)

**Input**: Feature specification from `specs/001-core-blackjack-engine/spec.md`

## Summary

Implement the deterministic, headless core Blackjack engine inside `backend/app/engine/` using a clean, decoupled modular file layout (`types.py`, `card.py`, `hand.py`, `shoe.py`, `rules.py`, `interfaces.py`, `settlement.py`, `round.py`). The engine maintains complete round and hand state machines, deals cards, dynamically validates legal actions per turn, enforces all configurable casino rules (S17/H17, American Peek vs ENHC, 3:2 / 6:5 / 1:1 payouts, DAS, RSA, Surrender, Insurance), calculates settlements with immediate bankroll deductions, and enables headless programmatic play from start to finish via external test controllers without hardcoded test hands.

---

## Technical Context

**Language/Version**: Python 3.12+ (managed by `uv`).

**Primary Dependencies**: Standard library Python (`dataclasses`, `enum`, `typing`, `random`), `numpy` (for vectorization/PRNG if needed), `pydantic` v2 (for rule configurations and DTO serialization).

**Storage**: Purely in-memory domain state. Zero database dependencies inside the engine package.

**Testing**: `pytest`, `pytest-asyncio` covering full round play, rule combinations, edge cases, and deterministic card injection.

**Target Platform**: Linux / macOS containerized (Docker) and headless local development.

**Project Type**: Standalone domain library module (`backend/app/engine/`).

**Performance Goals**: <2 ms execution turnaround per complete round in memory; capability to execute >10,000 rounds in seconds.

**Constraints**:
- Core Principle I: Zero UI, HTTP, or database dependencies in the engine.
- Core Principle IV: Strict seeded determinism; PRNG seed and FIFO test card injection.
- Zero hardcoded mock hands in production code.

**Scale/Scope**: 1 to 8 card decks, up to 4 split hands per round, full variable casino rules spectrum.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Gate | Requirement | Status | Notes |
|:---|:---|:---:|:---|
| **I. Engine Independence & Determinism** | Core game rules must reside exclusively in backend core services without UI/transport coupling. Headless simulation capability mandatory. | **PASS** | Resides entirely in `backend/app/engine/` with zero web, socket, or persistence dependencies. |
| **II. Tri-Entity Synchronization** | Engine must support isolated player table instances orchestrated centrally. | **PASS** | `BlackjackRound` instances are self-contained, allowing orchestrators to step tables in parallel. |
| **III. Provider Abstraction** | Engine must accept abstract decisions without knowledge of remote AI APIs. | **PASS** | Engine takes pure `Action` inputs via `submit_action()`, decoupled from AI providers. |
| **IV. Seeded Reproducibility** | Full deterministic reproducibility via random seed; PRNG seedable. | **PASS** | `Shoe` supports explicit integer seed and optional FIFO test card sequence injection. |
| **V. Telemetry & Persistence** | Engine must produce granular round, hand, decision, and bankroll records. | **PASS** | `RoundSettlement` and `RoundState` produce complete structured data payloads. |

---

## Project Structure

### Documentation (this feature)

```text
specs/001-core-blackjack-engine/
├── spec.md              # Feature specification with 5 clarified decision points
├── plan.md              # This implementation plan
├── research.md          # Phase 0 architectural research & decisions
├── data-model.md        # Phase 1 domain entity and state machine models
├── quickstart.md        # Phase 1 runnable test controller verification guide
├── contracts/           # Phase 1 interface specifications
│   └── engine_api.md    # RoundController, CardSource, and error contracts
└── checklists/
    └── requirements.md  # Spec quality checklist (16/16 verified)
```

### Source Code (repository root)

```text
backend/app/engine/
├── __init__.py          # Exports public API (BlackjackRound, TableRules, Shoe, Card, Action)
├── types.py             # Enums: Action, RoundPhase, HandStatus, Soft17Rule, DealerStyle, etc.
├── card.py              # Immutable Card (Suit, Rank, nominal value, is_ace)
├── hand.py              # Hand, PlayerHand, DealerHand, HandValue scoring & softness resolution
├── shoe.py              # Multi-deck Shoe (seeded shuffle, burn, cut-card penetration, FIFO injection)
├── rules.py             # TableRules dataclass/pydantic configuration
├── interfaces.py        # Abstract protocols (RoundController, CardSource) and domain exceptions
├── settlement.py        # Pure settlement arithmetic, insurance solving, bankroll delta calculation
└── round.py             # Main BlackjackRound state machine & test controller driver interface

backend/tests/
├── test_engine_round.py # Full lifecycle playthrough tests via test controller
├── test_engine_rules.py # Rule variation tests (S17/H17, Peek/ENHC, DAS, RSA, Surrender, Payouts)
└── test_engine_shoe.py  # Shoe shuffling, seeding, penetration, and FIFO injection tests
```

**Structure Decision**: Fully separates domain concerns across dedicated modules inside `backend/app/engine/`, directly honoring the user's specification: *"Create the engine inside backend/app/engine... Create the necessary classes and interfaces. You can use separate files like one file for types, another for the main, another for interfaces, etc."*

---

## Complexity Tracking

*No constitutional violations. All architecture adheres strictly to core principles.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|:---|:---|:---|
| *None* | N/A | N/A |
