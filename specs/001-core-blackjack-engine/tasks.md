# Tasks: Core Blackjack Engine

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)  
**Package**: `backend/app/engine/`  
**Date**: 2026-10-09

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize the engine module structure, dependencies, canonical types, and interface contracts.

- [x] T001 Initialize package directory `backend/app/engine/` and add `numpy` dependency via `uv add numpy` in `backend/pyproject.toml`
- [x] T002 [P] Implement all enums and value containers (`Action`, `RoundPhase`, `HandStatus`, `Soft17Rule`, `DealerStyle`, `SurrenderRule`, `SettlementOutcome`) in `backend/app/engine/types.py`
- [x] T003 [P] Implement abstract protocols (`RoundController`, `CardSource`, `RoundEventListener`) and domain exceptions (`EngineError`, `InvalidStateError`, `IllegalActionError`, `InvalidBetError`, `InsufficientFundsError`) in `backend/app/engine/interfaces.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core domain primitives (Card, Hand, Shoe) that MUST be complete before round execution and user stories can proceed.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T004 [P] Create unit tests for Card and Hand valuation in `backend/tests/test_engine_card_hand.py` covering card nominal values, dynamic Ace softness (11 to 1), 21 evaluation, natural Blackjack detection, and bust detection
- [x] T005 [P] Implement immutable `Card` class (`Suit`, `Rank`, nominal value, `is_ace`, code) in `backend/app/engine/card.py`
- [x] T006 Implement `HandValue`, `Hand`, `PlayerHand`, and `DealerHand` in `backend/app/engine/hand.py` with dynamic Ace softness reduction and natural Blackjack vs. split 21 distinction
- [x] T007 [P] Create unit tests for Shoe in `backend/tests/test_engine_shoe.py` covering multi-deck generation (1–8 decks), seeded PRNG shuffling, initial burn cards, cut-card penetration tracking, and FIFO test card injection
- [x] T008 Implement `Shoe` in `backend/app/engine/shoe.py` conforming to `CardSource` protocol with seeded shuffling, cut-card index tracking, burn card removal, and optional FIFO card sequence injection for external test controllers

**Checkpoint**: Foundation ready - card valuation and deterministic card supply are fully operational.

---

## Phase 3: User Story 1 - Full Deterministic Round Lifecycle Playthrough (Priority: P1) 🎯 MVP

**Goal**: Execute complete Blackjack rounds from opening bets through dealing, player actions (Hit, Stand), deterministic dealer resolution, and final settlement with immediate bankroll deduction.

**Independent Test**: Can be verified by running a test controller that initializes a round with an initial bet, queries legal actions, executes player decisions to completion, runs dealer drawing to terminal state, and settles payouts and bankroll changes.

### Tests for User Story 1 ⚠️

- [x] T009 [P] [US1] Create lifecycle playthrough unit tests in `backend/tests/test_engine_round.py` verifying initial betting, dealing, hit/stand transitions, deterministic dealer play (Hard/Soft 17), settlement, and immediate bankroll deductions

### Implementation for User Story 1

- [x] T010 [P] [US1] Implement `TableRules` in `backend/app/engine/rules.py` encapsulating casino variations (`S17`/`H17`, 3:2 payout, American Peek, DAS, table min/max limits)
- [x] T011 [US1] Implement baseline settlement resolution in `backend/app/engine/settlement.py` for standard win (1:1), push, natural blackjack, dealer bust, and player bust with immediate bankroll debit/credit calculations
- [x] T012 [US1] Implement core `BlackjackRound` finite state machine in `backend/app/engine/round.py` (`start_round`, `get_legal_actions`, `submit_action` for Hit and Stand, `play_dealer_to_end`, and `settle`)
- [x] T013 [US1] Export public engine API in `backend/app/engine/__init__.py` exposing `BlackjackRound`, `TableRules`, `Shoe`, `Card`, `Action`, and domain exceptions

**Checkpoint**: User Story 1 (MVP) is fully functional and independently testable end-to-end.

---

## Phase 4: User Story 2 - Comprehensive Rules Parameterization & Action Validation (Priority: P1)

**Goal**: Accurately enforce configurable casino rules (Soft 17 handling, payout ratios, American Peek vs ENHC with Total Bets Lost, and DAS) and reject all illegal actions.

**Independent Test**: Can be verified by initializing the engine with each rule variation (e.g., S17 vs H17, 3:2 vs 6:5 payouts, Peek vs ENHC) and verifying that dealer behavior, payouts, and action legality match configured constraints.

### Tests for User Story 2 ⚠️

- [x] T014 [P] [US2] Create rule variation and validation unit tests in `backend/tests/test_engine_rules.py` covering S17 vs H17, payout ratios (3:2, 6:5, 1:1), American Peek vs ENHC (with Total Bets Lost on dealer BJ), and illegal action rejections

### Implementation for User Story 2

- [x] T015 [US2] Implement deterministic dealer drawing rule evaluation in `backend/app/engine/hand.py` and `backend/app/engine/round.py` distinguishing `S17` (stand on soft 17) from `H17` (hit soft 17 until hard 17+)
- [x] T016 [US2] Implement American Peek vs European No Hole Card (ENHC) dealing and peek flow in `backend/app/engine/round.py` (checking hole card on Ace/10 upcard in Peek; deferring dealer second card in ENHC)
- [x] T017 [US2] Implement ENHC Total Bets Lost (TBL) payout logic in `backend/app/engine/settlement.py` ensuring player forfeits initial and doubled/split wagers against dealer Natural Blackjack
- [x] T018 [US2] Implement legal action validation in `backend/app/engine/round.py` verifying that invalid actions (e.g., doubling after hit, betting out of table bounds) raise `IllegalActionError` and `InvalidBetError` without corrupting round state

**Checkpoint**: User Stories 1 AND 2 are fully functional and verifiable.

---

## Phase 5: User Story 3 - Multi-Hand Split, Insurance & Side-Action Mechanics (Priority: P2)

**Goal**: Support complex split hands (sequential card dealing and execution), Double Down wagers, Insurance side bets against dealer Ace, and Surrender.

**Independent Test**: Can be verified by driving test controller rounds through split sequences (including pairs of 8s and split Aces), double downs, insurance offers, and surrender claims.

### Tests for User Story 3 ⚠️

- [x] T019 [P] [US3] Create split, double, insurance, and surrender tests in `backend/tests/test_engine_splits_sidebets.py` using FIFO injected card sequences in `Shoe`

### Implementation for User Story 3

- [x] T020 [US3] Implement `Double Down` action in `backend/app/engine/round.py` (verifying 2-card hand length, doubling bet, deducting bankroll immediately, dealing exactly one card, and transitioning hand to stood/busted)
- [x] T021 [US3] Implement sequential `Split` mechanics in `backend/app/engine/round.py` (splitting matching cards into two hands, deducting matching bet immediately, dealing second card to Hand 1 immediately, playing Hand 1 to completion, then dealing second card to Hand 2 and advancing active hand focus)
- [x] T022 [US3] Implement split limits and `Hit Split Aces` restriction in `backend/app/engine/round.py` (enforcing `max_split_hands`, `RSA` toggle, and auto-standing split Aces when hitting split Aces is disabled)
- [x] T023 [US3] Implement `Insurance` side bet in `backend/app/engine/round.py` and `backend/app/engine/settlement.py` (prompting on dealer Ace upcard, deducting 50% bet immediately, and paying 2:1 plus returned stake if dealer has Natural Blackjack)
- [x] T024 [US3] Implement `Surrender` action in `backend/app/engine/round.py` and `backend/app/engine/settlement.py` (verifying initial two-card eligibility, terminating hand immediately, and returning 50% of the initial bet)

**Checkpoint**: User Stories 1, 2, and 3 work seamlessly together with multi-hand and side-bet mechanics.

---

## Phase 6: User Story 4 - Deterministic Shoe Management & Penetration Tracking (Priority: P3)

**Goal**: Provide deterministic shoe state management with cut-card penetration triggers, burn cards, and discard recovery.

**Independent Test**: Can be verified by observing identical card sequences across repeated seeded runs, detecting cut-card threshold flags triggering between-rounds reshuffles, and validating discard tray recovery.

### Tests for User Story 4 ⚠️

- [x] T025 [P] [US4] Create shoe penetration, burn card, and seeded consistency tests in `backend/tests/test_engine_shoe.py`

### Implementation for User Story 4

- [x] T026 [US4] Implement cut-card penetration monitoring in `backend/app/engine/shoe.py` and `backend/app/engine/round.py` (setting `reshuffle_needed=True` when cut threshold is crossed, completing active round, and triggering full reshuffle before next round deal)
- [x] T027 [US4] Implement mid-round discard tray recovery in `backend/app/engine/shoe.py` (shuffling discards mid-round only if undealt cards in shoe are completely exhausted)

**Checkpoint**: All four user stories are completely functional, decoupled, and independently testable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validation against end-to-end quickstart scenarios, code quality audits, and documentation updates.

- [x] T028 [P] Validate quickstart validation scenarios from `specs/001-core-blackjack-engine/quickstart.md` in `backend/tests/test_quickstart.py`
- [x] T029 [P] Run linter and formatting checks across the new engine package via `ruff check backend/app/engine`
- [x] T030 Execute complete test suite verifying 100% test pass rate via `pytest backend/tests/test_engine*.py backend/tests/test_quickstart.py -v`
- [x] T031 Update `docs/` and module docstrings in `backend/app/engine/` detailing engine interfaces and usage examples

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Can begin immediately.
- **Foundational (Phase 2)**: Depends on Setup (T001-T003) - BLOCKS all User Stories.
- **User Story 1 (Phase 3)**: Depends on Foundational completion (T004-T008). Delivers MVP.
- **User Story 2 (Phase 4)**: Depends on User Story 1 completion (T009-T013).
- **User Story 3 (Phase 5)**: Depends on User Story 1 & 2 completion (T014-T018).
- **User Story 4 (Phase 6)**: Depends on Foundational Shoe completion; can run in parallel with US2/US3 or sequentially after US3.
- **Polish (Phase 7)**: Depends on all user stories being completed.

### Parallel Opportunities

- **Phase 1**: T002 (`types.py`) and T003 (`interfaces.py`) can be built in parallel.
- **Phase 2**: T004/T005 (`card.py`, tests) and T007/T008 (`shoe.py`, tests) can be built in parallel.
- **Phase 3**: T009 (tests) and T010 (`rules.py`) can be implemented in parallel.
- **Phase 4**: T014 (tests) can be created in parallel with rule definitions.
- **Phase 5**: T019 (tests) can be created in parallel.
- **Phase 7**: T028 (`test_quickstart.py`) and T029 (`ruff check`) can run in parallel.

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Complete Phase 1 (Setup) and Phase 2 (Foundational primitives: Card, Hand, Shoe).
2. Complete Phase 3 (User Story 1: Basic Round Lifecycle with Hit, Stand, Dealer Play, Settlement).
3. **STOP and VALIDATE**: Run `backend/tests/test_engine_round.py`. The engine is now capable of playing full rounds from start to finish via a test controller!

### Incremental Delivery
1. Add Phase 4 (User Story 2: Configurable rules & Peek/ENHC).
2. Add Phase 5 (User Story 3: Splits, Doubles, Insurance, Surrender).
3. Add Phase 6 (User Story 4: Shoe penetration & recovery).
4. Run Phase 7 (Polish & Quickstart validation).
