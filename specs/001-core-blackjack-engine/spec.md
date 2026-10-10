# Feature Specification: Core Blackjack Engine

**Feature Branch**: `001-core-blackjack-engine`

**Created**: 2026-10-09

**Status**: Draft

**Input**: User description: "Create the blackjack engine. This engine should be responsible of keeping a round and hand state, deal cards, validate actions, apply configured rules, solve insurance, bets, paids and results; determin which action corresponds to each turn. We should end with an engine that let us play rounds from start to finish given by a test controller. Do not make the test hands"

## Clarifications

### Session 2026-10-09
- Q: How should the test controller supply deterministic card sequences to the engine during tests without hardcoding test hands in the engine? (FR-012) → A: The `Shoe` accepts an optional pre-arranged card list dealt in exact FIFO order before falling back to seeded shuffling.
- Q: When a player splits a hand, how should the engine sequence the dealing of second cards to the split hands? (FR-006) → A: Sequential dealing: Deal a second card to Hand 1 and play it to completion, then deal a second card to Hand 2 and play it to completion.
- Q: When a player places an initial, double, split, or insurance bet, should the engine deduct funds from the player's bankroll immediately upon action placement? (FR-001, FR-009) → A: Immediate deduction: Deduct funds immediately as bets occur, with winnings and pushed stakes credited at settlement.
- Q: In European No Hole Card (ENHC) mode, if a player doubles or splits and the dealer achieves a Natural Blackjack, which rule applies to the player's additional wagers? (FR-007) → A: Total Bets Lost (TBL): Player loses initial bet plus all doubled/split bets against dealer Natural Blackjack.
- Q: When the cut-card penetration threshold is reached, at what point should the engine trigger the shoe reshuffle? (FR-008) → A: Between rounds: Complete current round with current shoe, then reshuffle before the next round (reshuffling discards mid-round only if cards are completely exhausted).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Full Deterministic Round Lifecycle Playthrough (Priority: P1)

As a simulation orchestrator or automated test controller, I want to execute complete Blackjack rounds from opening bets through initial deal, turn execution, dealer resolution, and final payout settlement, so that simulation entities can play valid, mathematically rigorous Blackjack games headlessly without UI or manual intervention.

**Why this priority**: Foundational core capability. Every simulation table, decision model benchmark, and betting evaluation depends entirely on executing complete rounds end-to-end under deterministic rules.

**Independent Test**: Can be tested independently by driving a round from a test controller: placing an initial bet within table limits, dealing cards, querying the current active turn, applying legal player actions until hands finish, executing dealer resolution, and verifying that the final round state, payouts, and bankroll transitions match official Blackjack rules.

**Acceptance Scenarios**:

1. **Given** a table initialized with standard rules and a funded player bankroll, **When** the controller places an initial bet and starts the round, **Then** the engine transitions to dealing state, distributes initial cards, and identifies the active turn.
2. **Given** an active player hand with a non-busting total, **When** the controller queries legal actions, **Then** the engine returns exactly the valid actions permissible for that specific hand state and rules configuration.
3. **Given** an active player hand, **When** the controller submits a valid action (Hit, Stand, Double, Split, Surrender), **Then** the engine applies the state mutation, deals subsequent cards if required, and advances turn order or transitions to dealer play.
4. **Given** all player hands have stood, doubled, busted, or surrendered, **When** the dealer turn executes, **Then** the dealer draws cards strictly according to deterministic dealer rules (standing on 17 or hitting Soft 17 per configuration) until reaching terminal state.
5. **Given** completion of the dealer turn, **When** settlement occurs, **Then** the engine accurately compares all active player hands against the dealer hand, determines victory, defeat, or push, calculates exact payout returns, and updates player bankroll.

---

### User Story 2 - Comprehensive Rules Parameterization & Action Validation (Priority: P1)

As a researcher configuring comparative simulations, I want the engine to enforce all configurable casino rules (Soft 17 handling, Blackjack payout ratios, American Peek vs ENHC, Double After Split, Resplit limits, and Surrender rules), so that decision models can be benchmarked across different casino environments.

**Why this priority**: Required by Core Principle I of the project constitution and project requirements (RF-01, RF-02). Simulation benchmarks must test how models adapt to variable table rules.

**Independent Test**: Can be tested independently by initializing the engine with various rule presets (e.g., S17 vs H17, 3:2 vs 6:5 payouts, Peek vs ENHC, DAS enabled vs disabled) and verifying that the engine enforces the corresponding constraints during play.

**Acceptance Scenarios**:

1. **Given** a table configured with `S17` (Dealer stands on Soft 17), **When** the dealer hand reaches Soft 17 (Ace counted as 11), **Then** the engine forces the dealer to Stand without drawing additional cards.
2. **Given** a table configured with `H17` (Dealer hits Soft 17), **When** the dealer hand reaches Soft 17, **Then** the engine forces the dealer to Hit until achieving Hard 17 or higher, or busting.
3. **Given** a table with American Peek enabled, **When** the dealer upcard is an Ace or 10-value card, **Then** the engine checks for natural dealer Blackjack before player actions begin; if dealer has Blackjack, the round immediately resolves.
4. **Given** a table with European No Hole Card (ENHC), **When** initial cards are dealt, **Then** the dealer receives only one card, players complete all decisions, and the dealer draws the second card at the end.
5. **Given** an active hand, **When** an invalid action is submitted (e.g., Doubling after a previous Hit, or Splitting non-matching cards), **Then** the engine rejects the action and preserves current state without side effects.

---

### User Story 3 - Multi-Hand Split, Insurance & Side-Action Mechanics (Priority: P2)

As a test controller, I want the engine to correctly manage split hands (creating independent hand instances, deducting additional bets, tracking resplit limits), optional insurance bets against dealer Ace upcards, and surrender settlements, so that advanced decision strategies are accurately simulated.

**Why this priority**: Split hands, insurance, and surrender represent high-variance decision points essential for calculating player edge and true count strategy deviations.

**Independent Test**: Can be tested independently by driving rounds through split scenarios, insurance prompts, and surrender requests, verifying that split hands are tracked and evaluated independently with their own bet amounts and card sequences.

**Acceptance Scenarios**:

1. **Given** an initial deal of matching rank cards (e.g., pair of 8s) and sufficient player bankroll, **When** the controller submits a Split action, **Then** the engine divides the hand into two independent hands, deducts an additional matching bet, immediately deals a second card to the first hand, and sets the first hand as active while the second split hand awaits its second card.
2. **Given** the first split hand reaches terminal state (stood, doubled, or busted), **When** the first hand completes, **Then** the engine automatically deals a second card to the second split hand and advances turn focus to it.
3. **Given** split Aces when `Hit Split Aces` is disabled, **When** each Ace receives its single required card, **Then** each hand immediately transitions to stood status without permitting further hits.
4. **Given** a dealer upcard of Ace when insurance is enabled, **When** the controller accepts insurance, **Then** the engine records an insurance side bet equal to half the initial main bet; if dealer reveals natural Blackjack, insurance pays 2:1.
5. **Given** a hand eligible for surrender, **When** surrender is accepted, **Then** the engine terminates the hand, refunds half the original bet, forfeits the remaining half to the house, and excludes the hand from dealer comparison.

---

### User Story 4 - Deterministic Shoe Management & Penetration Tracking (Priority: P3)

As a simulation controller, I want the engine to maintain a deterministically seeded card shoe (supporting 1 to 8 decks, initial burn cards, and cut-card penetration threshold detection), so that card depletion, Hi-Lo counts, and reshuffle conditions are tracked reproducibly across rounds.

**Why this priority**: Required by Core Principle IV (Seeded Reproducibility) to guarantee that any simulation run can be identically reproduced and audited.

**Independent Test**: Can be tested independently by initializing the shoe with a specific seed, recording the sequence of dealt cards, re-initializing with the same seed, and verifying that the dealt cards and burn sequences are identical.

**Acceptance Scenarios**:

1. **Given** a shoe initialized with a specific seed and deck count, **When** dealing cards across successive rounds, **Then** identical seeds produce exactly identical card sequences and hand outcomes.
2. **Given** a configured cut-card penetration percentage (e.g., 75%), **When** cards dealt exceed the cut threshold during a round, **Then** the engine completes the active round using the current shoe and flags that a reshuffle MUST occur before starting the next round.
3. **Given** a shoe configured with burn cards, **When** a new shoe is initialized, **Then** the engine discards the specified number of cards before the first round deal.

---

### Edge Cases

- **Natural Blackjack vs. 21 after Split**: A 2-card 21 on a split hand (e.g., Ace + 10 after split) is treated as a standard total of 21, NOT a natural Blackjack, and does not receive natural Blackjack bonus payouts unless explicitly configured.
- **Push on Dealer Blackjack**: When both player and dealer hold natural Blackjacks, the round resolves as a Push (main bet refunded), while any insurance bet still pays 2:1.
- **Double Down and Split Losses vs. Dealer Blackjack in ENHC**: In European No Hole Card (ENHC), because the dealer does not peek before player actions, if a player doubles or splits and the dealer subsequently achieves a Natural Blackjack, the player loses all staked bets (Total Bets Lost / TBL), including both initial and doubled/split wagers.
- **Resplit Cap Reached**: When a player splits and receives another matching card, further splits are permitted only if the total resulting hands do not exceed the configured `max_split_hands` limit.
- **Insufficient Bankroll for Double or Split**: If player bankroll is less than the required bet amount to double or split, the engine MUST mark Double and Split as illegal actions.
- **Simultaneous Bust Principle**: If a player hand busts (>21), that hand immediately loses its bet regardless of whether the dealer subsequently busts during the dealer turn.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The engine MUST maintain explicit, immutable state models for the table, round, dealer, and player hands throughout the round lifecycle, tracking immediate bankroll deductions upon bet commitment.
- **FR-002**: The round lifecycle MUST transition through explicit sequential stages:
  1. `BETTING`: Accepting player initial bets within configured table limits.
  2. `DEALING`: Distributing initial cards to player and dealer.
  3. `INSURANCE`: Offering and resolving insurance side bets when dealer upcard is Ace.
  4. `PEEK`: Evaluating dealer natural Blackjack before player actions (American style).
  5. `PLAYER_TURNS`: Sequencing active turns for player hands until all reach terminal status.
  6. `DEALER_TURN`: Executing deterministic dealer hit/stand rules.
  7. `SETTLEMENT`: Evaluating hand outcomes, calculating payouts, and updating bankrolls.
  8. `ROUND_COMPLETE`: Finalizing round telemetry and checking shoe penetration.
- **FR-003**: The engine MUST evaluate hand totals accurately:
  - Cards 2 through 9 hold their face numerical values.
  - 10, Jack, Queen, and King hold a value of 10.
  - Aces evaluate dynamically as 11 (Soft hand) or 1 (Hard hand) to produce the highest possible total not exceeding 21.
- **FR-004**: The engine MUST distinguish a Natural Blackjack (initial two cards consisting of an Ace and a 10-value card) from a 3+ card 21 or a 21 formed on a split hand.
- **FR-005**: The engine MUST enforce dealer drawing behavior strictly according to table configuration:
  - Dealer MUST hit on any total strictly less than 17.
  - Dealer MUST stand on Hard 17 through Hard 21.
  - On Soft 17 (total 17 with an Ace counted as 11), dealer MUST stand if configured with `S17`, or hit if configured with `H17`.
- **FR-006**: The engine MUST determine and expose legal actions for the currently active hand at each turn:
  - `Hit`: Always legal if hand total is strictly less than 21 and hand has not doubled or surrendered.
  - `Stand`: Always legal for any active hand.
  - `Double`: Legal only on initial 2 cards of a hand (and on split hands only if `DAS` is enabled), provided player bankroll covers the additional bet.
  - `Split`: Legal only when hand contains exactly two cards of equal rank/value, total split hands do not exceed `max_split_hands`, and player bankroll covers the additional bet. Split hands are dealt and played sequentially: Hand 1 receives its second card immediately and is played to completion before Hand 2 receives its second card.
  - `Surrender`: Legal only on initial two cards when permitted by table surrender rules.
- **FR-007**: The engine MUST support configurable table rules:
  - `soft_17_rule`: `S17` (stand) or `H17` (hit).
  - `blackjack_payout`: Ratio options `3:2` (1.5x), `6:5` (1.2x), or `1:1` (1.0x).
  - `hole_card_rule`: `AmericanPeek` (dealer checks hole card on Ace/10 before player acts) or `EuropeanNoHoleCard` (dealer draws second card after players finish; player forfeits total bets lost on double/split against dealer Natural Blackjack).
  - `insurance_enabled`: Boolean; payout fixed at 2:1.
  - `surrender_rule`: `None`, `Late`, or `Early`.
  - `double_after_split`: Boolean (`DAS`).
  - `max_split_hands`: Integer (typically 2 to 4).
  - `resplit_aces`: Boolean (`RSA`).
  - `hit_split_aces`: Boolean.
  - `min_bet` and `max_bet`: Numerical boundaries for initial bets.
- **FR-008**: The engine MUST manage shoe state deterministically:
  - Support 1, 2, 4, 6, or 8 standard 52-card decks.
  - Use a seedable pseudo-random number generator for card shuffling.
  - Discard configured burn cards upon shoe creation.
  - Track cut-card penetration: when reached, the engine completes the active round using the existing shoe and executes a full reshuffle prior to dealing the next round (reshuffling discards mid-round only if shoe cards are completely exhausted).
- **FR-009**: The engine MUST deduct all wagers (initial bets, doubles, splits, insurance) from the player's bankroll immediately upon action commitment, and resolve payouts at settlement:
  - Natural Blackjack win pays according to `blackjack_payout` ratio plus return of initial bet.
  - Standard player win pays 1:1 plus return of bet.
  - Dealer bust pays all surviving (non-busted, non-surrendered) player hands 1:1 plus return of bet.
  - Push returns original bet without net win/loss.
  - Player bust forfeits staked bet (already deducted).
  - Surrender returns 50% of the original bet.
  - Winning insurance pays 2:1 plus return of insurance bet; losing insurance forfeits insurance bet.
- **FR-010**: The engine MUST provide a clean, headless programmatic controller interface that allows driving rounds step-by-step without hardcoded or mock hands.
- **FR-011**: The engine MUST prevent illegal state mutations, raising descriptive domain errors when an invalid action, improper bet, or out-of-turn command is invoked.
- **FR-012**: The engine MUST NOT include hardcoded test hands inside production engine code; all card distributions must flow through the `Shoe`, which supports an optional pre-arranged card sequence (FIFO dealing) supplied at initialization for test controller scenarios before falling back to seeded generation.

### Key Entities

- **Shoe**: Container for 1-8 card decks with deterministic shuffling, burn card removal, card dealing pointer, penetration monitoring, and support for an optional pre-arranged FIFO card sequence for external test controllers.
- **Card**: Immutable representation of rank (2-10, J, Q, K, A) and suit (Hearts, Diamonds, Clubs, Spades) with blackjack valuation methods.
- **Hand**: Collection of cards belonging to a player or dealer, tracking active bet, double status, split status, bust status, and soft/hard total.
- **RoundState**: Snapshot of the complete round, including current phase, dealer hand, list of player hands, active hand index, shoe status, and historical action log.
- **TableRules**: Immutable configuration object encapsulating all variable rule toggles (S17/H17, payout ratios, Peek/ENHC, DAS, RSA, surrender mode, table limits).
- **RoundSettlement**: Outcome report detailing per-hand results (Win, Loss, Push, Blackjack, Surrender), insurance results, and net bankroll adjustments.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An automated test controller can execute 1,000 complete, sequential rounds headlessly with 100% mathematical and rule consistency.
- **SC-002**: 100% of illegal player actions (e.g., doubling on a 3-card hand, splitting non-pairs, betting below table minimum) are rejected with zero corruptions of game state.
- **SC-003**: Given identical seed, rules configuration, and sequence of player actions, 100% of generated rounds produce byte-for-byte identical game logs and bankroll outcomes.
- **SC-004**: Execution of a complete round (deal, 2 player hits, stand, dealer play, settlement) executes in under 2 milliseconds in memory.
- **SC-005**: Zero hardcoded test hands exist in the engine core code; all custom testing cards are supplied solely via external controller injection interfaces.

## Assumptions

- The engine is designed as a standalone, zero-dependency domain module residing in `backend/app/blackjack/`.
- The engine operates purely in-memory and does not perform network I/O, database writes, or UI rendering.
- Test suites will use external controller utilities to verify specific edge cases by supplying controlled card sequences into the shoe without modifying engine internals.
- A player holds a single initial hand per round, which may branch into multiple hands via splits up to `max_split_hands`.
