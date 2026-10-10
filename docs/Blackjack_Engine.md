# Core Blackjack Engine Architecture & API Reference

**Package**: `backend/app/engine/`  
**Version**: `0.1.0`  
**Type**: Zero-dependency deterministic domain engine

---

## 1. Overview

The Core Blackjack Engine is a pure in-memory, deterministic finite-state-machine (FSM) implementation of casino Blackjack. It is completely decoupled from UI, HTTP frameworks, database models, and network I/O, designed specifically for headless test controllers, simulation orchestrators, and AI decision model benchmarks.

### Core Capabilities
- **Strict FSM Lifecycle**: `AWAITING_BET` → `DEALING` → `INSURANCE_OFFERED` → `DEALER_PEEK` → `PLAYER_TURNS` → `DEALER_TURN` → `SETTLEMENT` → `ROUND_COMPLETE`.
- **Immediate Bankroll Accounting**: Stakes for initial bets, double downs, split hands, and insurance are debited immediately upon action commitment; winning payouts and returned stakes are credited at settlement.
- **Configurable Casino Rules**:
  - `Soft17Rule`: Stand on Soft 17 (`S17`) or Hit Soft 17 (`H17`).
  - `DealerStyle`: American Peek (`AMERICAN_PEEK`) vs European No Hole Card (`EUROPEAN_NO_HOLE_CARD` / `ENHC`).
  - `Payout Ratios`: 3:2 (1.5x), 6:5 (1.2x), 1:1 (1.0x).
  - `Double After Split (DAS)`: Toggleable.
  - `Resplit Aces (RSA)` & `Hit Split Aces`: Configurable restrictions.
  - `SurrenderRule`: Late surrender (`LATE`), Early (`EARLY`), or None (`NONE`).
- **Sequential Split Dealing**: When splitting, Hand 1 receives its second card immediately and is played to completion before Hand 2 receives its second card.
- **Total Bets Lost (TBL)**: In ENHC, dealer Natural Blackjack claims all initial, doubled, and split wagers.
- **Deterministic Multi-Deck Shoe**: PRNG-seeded shuffling, burn cards, cut-card penetration tracking, and discard recovery.
- **FIFO Test Injection**: External test controllers inject exact card sequences into `Shoe(card_sequence=[...])` without any hardcoded test hands in the engine codebase.

---

## 2. Architecture & File Structure

```
backend/app/engine/
├── __init__.py         # Public exports (BlackjackRound, TableRules, Shoe, Card, Enums, Exceptions)
├── card.py             # Card, Suit, Rank value objects
├── hand.py             # Hand, PlayerHand, DealerHand, HandValue (dynamic Ace softness)
├── interfaces.py       # RoundController, CardSource protocols and domain exceptions
├── round.py            # BlackjackRound state machine & RoundState snapshot
├── rules.py            # TableRules configuration model
├── settlement.py       # Pure settlement arithmetic (HandSettlement, RoundSettlement)
├── shoe.py             # Multi-deck Shoe (1-8 decks), PRNG seed, cut-card, discard recovery
└── types.py            # Canonical enums (Action, RoundPhase, HandStatus, etc.)
```

---

## 3. Quickstart Example

```python
from app.engine import BlackjackRound, TableRules, Shoe, Action, RoundPhase

# 1. Initialize rules, deterministic shoe, and player bankroll
rules = TableRules(min_bet=10.0, max_bet=500.0, soft_17_rule="S17", blackjack_payout_ratio=1.5)
shoe = Shoe(num_decks=6, seed=42)
engine = BlackjackRound(rules=rules, shoe=shoe, player_bankroll=1000.0)

# 2. Start round with initial bet
state = engine.start_round(bet=50.0)
assert engine.current_bankroll == 950.0  # Immediately deducted

# 3. Handle insurance if offered
if state.phase == RoundPhase.INSURANCE_OFFERED:
    state = engine.submit_insurance(accept=False)

# 4. Execute player actions
while state.phase == RoundPhase.PLAYER_TURNS:
    legal_actions = engine.get_legal_actions()
    if Action.HIT in legal_actions and state.player_hands[state.active_hand_index].total < 17:
        state = engine.submit_action(Action.HIT)
    elif Action.STAND in legal_actions:
        state = engine.submit_action(Action.STAND)

# 5. Execute deterministic dealer resolution
if state.phase == RoundPhase.DEALER_TURN:
    state = engine.play_dealer_to_end()

# 6. Settle round and inspect financial report
if state.phase == RoundPhase.SETTLEMENT:
    settlement = engine.settle()
    print(f"Final Bankroll: {settlement.final_bankroll}")
    print(f"Net Profit: {settlement.net_profit}")
    for hand_res in settlement.hand_outcomes:
        print(f"  Hand {hand_res.hand_index}: {hand_res.outcome.value} (Payout: {hand_res.payout})")
```

---

## 4. Test Controller Card Injection (Zero Mocking)

To verify specific card arrangements and edge cases deterministically without hardcoding cards in the engine:

```python
from app.engine import BlackjackRound, TableRules, Shoe, Card, Suit, Rank, Action

test_cards = [
    Card(Suit.HEARTS, Rank.EIGHT),     # Player card 1
    Card(Suit.CLUBS, Rank.SEVEN),      # Dealer upcard
    Card(Suit.SPADES, Rank.EIGHT),     # Player card 2 (pair of 8s)
    Card(Suit.DIAMONDS, Rank.SEVEN),   # Dealer hole card
    Card(Suit.HEARTS, Rank.THREE),     # Hand 1 split draw
    Card(Suit.SPADES, Rank.TEN),       # Hand 1 hit
    Card(Suit.CLUBS, Rank.TEN),        # Hand 2 split draw
]

shoe = Shoe(card_sequence=test_cards)
engine = BlackjackRound(rules=TableRules(), shoe=shoe, player_bankroll=1000.0)
engine.start_round(bet=50.0)

# Split pair of 8s
engine.submit_action(Action.SPLIT)
# Play Hand 1, then Hand 2 sequentially
```

---

## 5. Domain Exceptions

All domain exceptions inherit from `EngineError`:
- `InvalidStateError`: Invoking a method during an incompatible round phase.
- `IllegalActionError`: Submitting an action not currently legal for the active hand.
- `InvalidBetError`: Placing an opening bet outside table boundaries (`min_bet`, `max_bet`).
- `InsufficientFundsError`: Staking a bet, double, split, or insurance exceeding available bankroll.
- `ShoeEmptyError`: Attempting to deal when shoe and discard tray are depleted.
