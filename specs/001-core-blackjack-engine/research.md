# Research & Architectural Decisions: Core Blackjack Engine

**Feature**: [spec.md](spec.md)  
**Location**: `backend/app/engine/`  
**Date**: 2026-10-09

## 1. Modular Package Architecture & File Separation

### Decision
Structure the engine inside `backend/app/engine/` using dedicated single-responsibility modules:
- `types.py`: All canonical enumerations and lightweight value containers (`Action`, `RoundPhase`, `HandStatus`, `DealerStyle`, `SurrenderRule`, `Soft17Rule`, `SettlementOutcome`).
- `card.py`: Immutable `Card` representation (`Suit`, `Rank`, nominal/blackjack value).
- `hand.py`: `Hand`, `PlayerHand`, and `DealerHand` classes encapsulating dynamic score evaluation, Ace softness resolution, natural 21 detection, and bust detection.
- `shoe.py`: Multi-deck `Shoe` supporting deterministic PRNG seeding (via `random.Random` or `numpy.random`), cut-card penetration tracking, initial burn cards, and FIFO card sequence injection for test controllers.
- `rules.py`: Pydantic/dataclass `TableRules` encapsulating casino variations (S17 vs H17, Peek vs ENHC, 3:2 vs 6:5 payouts, DAS, RSA, max splits, table betting limits).
- `interfaces.py`: Abstract protocols (`RoundController`, `CardDealer`, `RoundEventListener`).
- `settlement.py`: Pure function settlement engine resolving main wagers, insurance, doubles, splits, surrenders, and net bankroll adjustments.
- `round.py`: Central `BlackjackRound` finite state machine governing the step-by-step round lifecycle.
- `__init__.py`: Clean public API export.

### Rationale
- Completely fulfills the user requirement: *"Create the engine inside backend/app/engine... Create the necessary classes and interfaces. You can use separate files like one file for types, another for the main, another for interfaces, etc."*
- Enforces Core Principle I of the constitution: engine is 100% decoupled from web frameworks, databases, and UI code.
- Prevents circular imports and simplifies unit test targeting.

### Alternatives Considered
- Single monolithic `engine.py` file: Rejected because splitting rules, cards, shoe, hand states, and round FSM into distinct files makes each unit independently testable and readable.
- Placing inside `backend/app/blackjack/`: The user explicitly instructed: `Create the engine inside backend/app/engine`. We follow the user's specific path directive.

---

## 2. Dynamic Hand Scoring & Ace Softness Resolution

### Decision
Implement hand scoring dynamically in `Hand.evaluate()`:
- Sum nominal values (2-9 face value, 10/J/Q/K as 10, Aces initially counted as 11).
- If total > 21 and count of Aces evaluated at 11 > 0, demote Aces from 11 to 1 one by one until total <= 21 or all Aces are hard (value 1).
- Return an immutable `HandValue(total: int, is_soft: bool, is_busted: bool, is_blackjack: bool)`.
- Explicitly flag `is_blackjack` as `True` ONLY IF the hand contains exactly 2 cards, total is 21, and `is_split == False`.

### Rationale
- Mathematical fidelity: Soft hands permit players/dealers to hit without immediate bust risk.
- Rigorous distinction: A 21 achieved on a split hand (e.g. Ace + Ten after split) is scored as 21 (`is_blackjack=False`), which avoids illegitimate 3:2 bonus payouts.

### Alternatives Considered
- Pre-computing a lookup table: Unnecessary complexity for 2–10 card hands; dynamic calculation executes in <1 microsecond.

---

## 3. Seeded Shoe Mechanics & Test Controller FIFO Injection

### Decision
Implement `Shoe` with dual-mode card generation:
1. Standard / Simulation Mode: Initialized with `num_decks` (1–8) and `seed` (optional int). Uses `random.Random(seed)` to shuffle standard 52-card decks. Discards `burn_cards` count. Sets `cut_card_index = int(total_cards * penetration)`.
2. Test Controller Mode (FIFO Injection): Constructor accepts an optional `card_sequence: list[Card]`. If provided, cards are dealt from this list first in FIFO order. Once the injected list is exhausted (or if omitted), it draws from the seeded shoe.
3. Reshuffle Rule: When cut-card is reached during a round, the shoe sets `reshuffle_needed = True`, allowing the active round to complete, and executes reshuffle prior to the subsequent round deal.

### Rationale
- Satisfies clarification Q1 and user requirement: *"Do not make the test hands"*. Production engine has zero mock hands; test controllers can cleanly inject card sequences via the `Shoe(card_sequence=[...])` parameter.
- Satisfies clarification Q5: Reshuffle occurs between rounds, preserving active hand counts.
- Satisfies Core Principle IV: Strict reproducibility.

### Alternatives Considered
- Mocking the random function via monkeypatching: Fragile and tightly coupled to implementation details. Pre-arranged FIFO list injection is clean, explicit, and self-contained.

---

## 4. Round Finite State Machine & Legal Action Determination

### Decision
The `BlackjackRound` transitions through strict sequential phases:
`BETTING` → `INITIAL_DEAL` → `INSURANCE_OFFERED` → `DEALER_PEEK` → `PLAYER_TURNS` → `DEALER_TURN` → `SETTLEMENT` → `ROUND_COMPLETE`.

At each player turn, `get_legal_actions()` dynamically checks:
- `STAND`: Always legal for active non-busted hand.
- `HIT`: Legal if hand total < 21 and hand has not doubled/surrendered.
- `DOUBLE`: Legal if hand length == 2, player bankroll >= hand bet, and (if split hand, `rules.double_after_split` is True).
- `SPLIT`: Legal if hand length == 2, card 1 rank/value == card 2 rank/value, total split hands < `rules.max_split_hands`, and player bankroll >= hand bet.
- `SURRENDER`: Legal on initial 2 cards if `rules.surrender_rule != SurrenderRule.NONE`.

Split hand progression follows Clarification Q2:
- Hand 1 receives card 2 immediately and is played to terminal state before Hand 2 receives card 2 and begins play.

### Rationale
- Enforces strict rules validity before action execution, raising domain exceptions (`IllegalActionError`, `InvalidStateError`) on violations.
- Allows test controllers and AI players to programmatically inspect what actions are legal.

---

## 5. Payout Precision & Bankroll Settlement

### Decision
Use `decimal.Decimal` or rounded float (`round(val, 2)`) for monetary wagers and settlements:
- Immediate Deduction (Clarification Q3): As soon as a bet is placed (initial bet, double down, split bet, insurance), the amount is deducted from `player.bankroll`.
- Settlement Credits (Clarification Q4 & Q3):
  - Natural Blackjack: credits `bet + bet * payout_ratio` (e.g. 3:2 payout on $10 credits $10 + $15 = $25).
  - Standard Win: credits `bet + bet * 1.0` ($20).
  - Push: credits `bet` (stake returned).
  - Loss / Bust: credits $0 (stake already deducted).
  - Surrender: credits `bet * 0.5`.
  - Insurance Win: credits `insurance_bet + insurance_bet * 2.0` ($15 for a $5 bet).
  - ENHC Dealer BJ (Clarification Q4): Player loses initial and double/split wagers (TBL - Total Bets Lost).
- Produces a comprehensive `RoundSettlement` summary.

### Rationale
- Prevents floating-point drift and negative bankroll anomalies.
- Matches `docs/Diseño Base de Datos (Modelo ER).md` transactional bankroll model.
