# Feature Specification: Full Basic Strategy Player & Decision Comparison Service

**Feature Branch**: `003-basic-strategy-player`

**Created**: 2026-10-11

**Status**: Draft

**Input**: User description: "Let's make the blackjacks basic strategy player. This will be based on the strategy that is writen inside docs/Estrategia Optima.md so no guesses should be made by this player. You should replace the mockup basic strategy player with this new player and we should be able to later compare the basic strategy player with the other players (Jev and Laya) in later specs, so you need a way to comunicate the basic strategy decision's with the other players choices. Some basic strategy. At the end of this spec, we should have a fully functional player that uses the basic strategy, connected to the orchestrator and ready to be used."

## Clarifications

### Session 2026-10-11
- Q: How should the system track and supply the True Count (TC) to the Basic Strategy Player for its bet sizing and decisions? (FR-008) → A: Agent-Internal Shoe Observer (Option B): The Basic Strategy Player maintains its own internal Hi-Lo card counting state (observing visible cards dealt at its table or shoe events, tracking Running Count, estimating remaining decks, and deriving True Count). It can also accept an override True Count if provided in `DecisionContext`.
- Q: How should the Decision Comparison Service integrate with the orchestrator during multi-agent simulations? (FR-009) → A: Inline Telemetry & Metrics (Option A): Evaluate decisions in real-time during turns; attach comparison results (`DecisionComparison`) directly to `DECISION_APPLIED` telemetry events and update cumulative deviation counts in table metrics.
- Q: When the Basic Strategy Player decides its opening round bet based on True Count, how should the orchestrator retrieve this bet amount? (FR-008) → A: Provider Method `get_bet` (Option A): Add an optional `get_bet(bankroll: float, min_bet: float) -> float` to the `DecisionProvider` protocol. The table/orchestrator queries this before starting a round; if not implemented by an agent, it defaults to `min_bet`.
- Q: When the table shoe reshuffles between rounds (crossing the cut card), how should the Basic Strategy Player reset its Hi-Lo card count? (FR-008) → A: Table-Triggered Count Reset (Option A): The player exposes a `reset_count()` method that the `EntityTable` automatically invokes whenever a new shoe generation is adopted or a shoe reshuffle occurs before a round.
- Q: How does the comparison evaluate other players (Jev/Laya) when they hold different cards or bet different amounts than the standalone Basic Strategy table? (FR-009, FR-010) → A: Contextual Position & Bet Comparison: The comparison oracle is evaluated *in the context of the specific player's table*. If Player A holds 15 vs dealer 2, the oracle evaluates what Basic Strategy dictates for 15 vs 2 (even though the standalone Basic Strategy player might hold 12 vs 5 at its own table). For opening bets, the oracle compares the player's wager against what Basic Strategy with bet spread dictates given that table's True Count and table minimum bet.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Full Optimal Strategy Table Decision Execution (Priority: P1)

As a simulation runner or benchmark analyst, I want the Basic Strategy Player to strictly adhere to the complete game theory decision matrix documented in `docs/Estrategia Optima.md` without guessing or heuristics, so that the player serves as a 100% mathematically sound baseline in simulations.

**Why this priority**: Core foundation of the feature. The user explicitly requires that no guesses are made and that the strategy accurately encodes all rules from `docs/Estrategia Optima.md` (Hard totals, Soft totals, Pair splitting with DAS conditions, Surrender, and Insurance rejection).

**Independent Test**: Can be tested independently by evaluating hand state combinations across all dealer upcards (2 through Ace) against the exact matrix rules in `docs/Estrategia Optima.md` and verifying 100% exact action matching without fallback defaults or unhandled branches.

**Acceptance Scenarios**:

1. **Given** a player hard total of 9 to 16 against any dealer upcard (2–A), **When** requesting a decision, **Then** the player returns the exact action specified in the Hard Totals matrix (e.g. 11 doubles vs 2–A, 10 doubles vs 2–9 and hits vs 10/A, 12 stands vs 4–6 and hits vs 2–3 & 7–A, 13–16 stands vs 2–6 and hits vs 7–A).
2. **Given** a player soft total (A,2 through A,9) against any dealer upcard, **When** requesting a decision, **Then** the player returns the exact action specified in the Soft Totals matrix (e.g. A,7 doubles/stands vs 2–6, stands vs 7–8, hits vs 9–A; A,2/A,3 doubles vs 5–6; A,8/A,9 always stands).
3. **Given** a pair of cards and Double After Split (DAS) permitted by table rules, **When** requesting a decision, **Then** the player splits pairs according to the Pair Splitting matrix (A,A and 8,8 always split; 6,6 splits vs 2–6 if DAS or 3–6 if no DAS; 4,4 splits vs 5–6 only if DAS; 5,5 and 10,10 never split).
4. **Given** a 2-card hand of 16 against dealer 9, 10, or A, or a hand of 15 against dealer 10, **When** surrender is permitted by table rules, **Then** the player chooses `SURRENDER`; if surrender is not allowed, the player defaults to the corresponding hard total action (Hit).
5. **Given** an insurance offer (dealer shows an Ace), **When** insurance is evaluated, **Then** the player strictly declines insurance (`can_insure = False` / `INSURANCE_DECLINE`), adhering to "INSURANCE OR EVEN MONEY: DON'T TAKE".

---

### User Story 2 - Dynamic True Count Bet Sizing (Priority: P1)

As a simulation controller, I want the Basic Strategy Player to compute the appropriate initial round wager based on the table minimum bet and the prevailing True Count (TC) as defined in `docs/Estrategia Optima.md`, so that the player reflects a complete, bankroll-aware card counting advantage player.

**Why this priority**: Part of the complete optimal strategy defined in section 7 of `docs/Estrategia Optima.md`. Wager sizing dictates long-term expected value and bankroll trajectory in simulations.

**Independent Test**: Can be tested independently by supplying varying True Counts ($\leq 0$, $+1$, $+2$, $+5$) with a minimum bet (e.g. $50) and a bet spread configuration (e.g. 1–12), verifying that calculated bet sizes equal the minimum bet when $TC \leq 0$ and $N \times \text{min\_bet}$ when $TC = N > 0$ (capped at spread maximum).

**Acceptance Scenarios**:

1. **Given** a running simulation where the shoe True Count is $\leq 0.0$, **When** determining the opening wager for a round, **Then** the player wagers exactly 1 unit (table minimum bet).
2. **Given** a shoe True Count of $+2.0$ with a table minimum bet of $50, **When** determining the opening wager, **Then** the player wagers exactly $2 \times \$50 = \$100$.
3. **Given** a shoe True Count exceeding the maximum bet spread factor (e.g., $TC = +15$ with spread 1–12), **When** determining the opening wager, **Then** the player caps the wager at 12 units ($12 \times \text{min\_bet}$).
4. **Given** a player bankroll smaller than the calculated spread wager, **When** placing the bet, **Then** the player wagers the remaining bankroll or table minimum without exceeding available funds.

---

### User Story 3 - Decision & Bet Comparison Evaluation Oracle (Priority: P2)

As an analytical evaluator or researcher running multi-agent benchmarks, I want an evaluation oracle (`DecisionComparator`) that compares any other agent's decisions and bets (such as Jev or Laya) against what Basic Strategy would dictate in that exact player's position, so that deviations in both hand play and card counting bet sizing are systematically captured even when tables diverge in hand composition or shoe state.

**Why this priority**: Core user requirement: Jev and Laya might be dealt different cards than the standalone Basic Strategy player (e.g. standalone Basic Strategy plays 12 vs 5, while Jev plays 15 vs 2). The system must evaluate what Basic Strategy would have done with Jev's exact hand (15 vs 2) and True Count bet sizing at Jev's table.

**Independent Test**: Can be tested independently by:
1. Passing a player hand state (e.g., 15 vs dealer 2) and agent choice (e.g. Stand or Hit) to verify the oracle evaluates the optimal action for that specific position.
2. Passing an opening bet wager (e.g., $50) with a specific True Count (e.g., +2 with $50 min bet) to verify the oracle identifies the optimal bet ($100) and delta ($50 underbet).

**Acceptance Scenarios**:

1. **Given** an action chosen by another agent (Jev or Laya) and the current table `DecisionContext` (e.g. 15 vs dealer 2, while the standalone Basic Strategy table plays 12 vs 5), **When** evaluated against the Basic Strategy oracle, **Then** the comparison service evaluates what basic strategy dictates for that specific player's hand and dealer upcard (e.g. Stand on 15 vs 2) and determines whether the chosen action is optimal (`is_optimal: bool`).
2. **Given** an opening round bet placed by another agent and that table's current True Count and minimum bet, **When** evaluated against the Basic Strategy bet oracle, **Then** the service computes the expected basic strategy bet according to the bet spread formula and outputs a bet comparison record (`optimal_bet`, `actual_bet`, `is_bet_optimal: bool`, `bet_delta: float`).
3. **Given** a suboptimal action chosen by an agent (e.g., Hit instead of Stand, or underbetting by $50 at TC +2), **When** evaluated, **Then** the comparison service outputs a comparison record containing the agent's action/bet, the optimal action/bet, the rule rationale from the strategy chart, and deviation categorization.
4. **Given** multi-agent round telemetry broadcast during orchestrator execution, **When** an agent places a bet or makes a move, **Then** the comparison result is attached to event telemetry (`DECISION_APPLIED` and round start) and reflected in table comparative metrics without modifying the agent's isolated table state.

---

### User Story 4 - Seamless Orchestrator Integration & Replacement (Priority: P2)

As a simulation orchestrator operator, I want the new full Basic Strategy player to seamlessly replace the existing mockup implementation across the orchestrator, test suites, and simulation tables without breaking the `DecisionProvider` protocol or existing test coverage, so that multi-agent benchmarks operate with the realistic player immediately.

**Why this priority**: Required by the user prompt ("You should replace the mockup basic strategy player with this new player ... connected to the orchestrator and ready to be used").

**Independent Test**: Can be tested independently by running all existing simulation orchestrator tests (`test_simulation_orchestrator.py`, `test_simulation_table.py`, `test_simulation_quickstart.py`, etc.) with the new Basic Strategy player and verifying 100% test pass rate with zero regression.

**Acceptance Scenarios**:

1. **Given** the simulation orchestrator registering an entity with `EntityType.OPTIMAL`, **When** instantiating tables, **Then** the new Basic Strategy player is attached as the default optimal decision provider.
2. **Given** multi-round simulations orchestrated across tables, **When** rounds execute, **Then** the player provides decisions asynchronously complying with the `DecisionProvider` protocol (`get_decision` returning `AgentDecision`).
3. **Given** 100% of existing tests in `backend/tests/`, **When** the test suite executes, **Then** all tests pass cleanly without errors.

---

### Edge Cases

- **Doubling Not Permitted After Hit / On Split**:
  - *Scenario*: The strategy chart specifies `D` (Double) or `Ds` (Double, else Stand), but the hand already has more than 2 cards or table rules restrict doubling (e.g. no DAS on split hands).
  - *Resolution*: Strictly follow chart fallback rules: for `D`, fallback to `HIT`; for `Ds`, fallback to `STAND`.
- **Surrender Not Offered or Not Allowed**:
  - *Scenario*: The chart specifies `SUR` (Surrender on 16 vs 9/10/A, or 15 vs 10), but table rules disable surrender (`surrender_rule == SurrenderRule.NONE`) or the hand has hit.
  - *Resolution*: Follow chart fallback: for 16 vs 9/10/A, hit; for 15 vs 10, hit.
- **Pair Splitting Without DAS**:
  - *Scenario*: Pair splitting chart specifies `Y/N` (Split if DAS, else No Split) for 2,2 / 3,3 vs 2–3, 4,4 vs 5–6, or 6,6 vs 2.
  - *Resolution*: If table rules have `double_after_split=False`, the player strictly plays the hand as a hard total (e.g. 4,4 becomes hard 8 $\rightarrow$ Hit; 6,6 becomes hard 12 $\rightarrow$ Hit vs 2).
- **Split Aces Rule (No Further Hits)**:
  - *Scenario*: Player splits Aces and receives a card, total is soft 18 or soft 19, but `hit_split_aces` is False.
  - *Resolution*: Engine automatically terminates hand; player respects engine legal actions list.
- **Multi-Card Soft Hands**:
  - *Scenario*: Hand contains Ace, 2, 4 (soft 17) and doubling is not legal (more than 2 cards).
  - *Resolution*: Evaluates as soft 17 under soft table: double is requested, fallback is `HIT`.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Basic Strategy Player MUST implement the `DecisionProvider` protocol and be categorized as `EntityType.OPTIMAL`.
- **FR-002**: The player MUST strictly encode the Hard Totals matrix from `docs/Estrategia Optima.md` covering totals 8 through 17+ against dealer upcards 2 through Ace, with zero guessing or heuristic deviation.
- **FR-003**: The player MUST strictly encode the Soft Totals matrix from `docs/Estrategia Optima.md` covering totals A,2 through A,9 against dealer upcards 2 through Ace.
- **FR-004**: The player MUST strictly encode the Pair Splitting matrix from `docs/Estrategia Optima.md` covering pairs 2,2 through A,A against dealer upcards 2 through Ace, incorporating conditional Double After Split (`Y/N`) rules based on active `TableRules.double_after_split`.
- **FR-005**: The player MUST strictly encode the Surrender rules from `docs/Estrategia Optima.md` (16 vs 9, 10, A; 15 vs 10) when surrender is a legal action in the current game state, falling back to Hit if surrender is unavailable.
- **FR-006**: The player MUST strictly decline Insurance and Even Money in all circumstances, adhering to the strategy mandate "INSURANCE OR EVEN MONEY: DON'T TAKE".
- **FR-007**: When a chart action requires doubling (`D` or `Ds`) but doubling is illegal (due to multi-card hand, bankroll restriction, or table rules), the player MUST fall back to `HIT` for `D` and `STAND` for `Ds`.
- **FR-008**: The player MUST maintain an internal Hi-Lo card counting observer to track observed dealt cards, expose `reset_count()` to reset counting state upon shoe reshuffle/adoption, and implement `get_bet(bankroll: float, min_bet: float) -> float` to calculate opening round wagers based on True Count (TC) and table minimum bet: 1 unit when $TC \leq 0$, and $\min(N, \text{max\_spread}) \times \text{min\_bet}$ when $TC = N > 0$ (default bet spread 1–12), with support for external TC override via `DecisionContext.true_count`.
- **FR-009**: The system MUST provide a Decision Comparison Service / Oracle (`DecisionComparator`) capable of evaluating any agent's decision or opening bet against what Basic Strategy dictates *in that agent's specific table position* (evaluating that player's cards and dealer upcard regardless of other tables' hands, and evaluating that player's opening bet against the Hi-Lo bet spread for that table's True Count).
- **FR-010**: The Decision Comparison Service MUST return structured comparison records:
  - For turn decisions: `DecisionComparison` indicating `is_optimal: bool`, optimal action, actual action, reasoning, category (`HARD_TOTAL`, `SOFT_TOTAL`, `PAIR_SPLIT`, `SURRENDER`, `INSURANCE`), and legality.
  - For round bets: `BetComparison` indicating `is_bet_optimal: bool`, optimal bet amount based on table True Count and spread rules, actual bet amount, bet difference (`bet_delta`), and prevailing True Count.
  - The orchestrator MUST attach these comparison payloads inline to `DECISION_APPLIED` and round start telemetry events and track cumulative optimality metrics per entity table.
- **FR-011**: The system MUST replace the placeholder/mockup implementation of `BasicStrategyAgent` with this complete implementation without breaking existing orchestrator controllers or table integrations.
- **FR-012**: The Basic Strategy Player MUST execute deterministically and in-memory with zero network, database, or UI dependencies.

---

### Key Entities

- **BasicStrategyPlayer**: Concrete implementation of `DecisionProvider` executing the decision matrices and bet sizing logic from `docs/Estrategia Optima.md`.
- **StrategyMatrix**: Internal lookup structures representing hard totals, soft totals, pair splits, and surrender recommendations indexed by player hand representation and dealer upcard.
- **DecisionComparison**: Value container holding comparative evaluation between an agent's turn action and the optimal basic strategy choice for that specific hand and dealer upcard.
- **BetComparison**: Value container holding comparative evaluation between an agent's opening bet and the optimal basic strategy bet sizing given that table's True Count.
- **DecisionComparator**: Service / utility protocol providing position-specific decision and bet comparison evaluations between decision providers and basic strategy.
- **BetSpreadConfig**: Configuration model specifying minimum bet, maximum spread multiplier, and True Count thresholds.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of cells across all 4 strategy charts in `docs/Estrategia Optima.md` (Hard totals: 100 hand-dealer combinations; Soft totals: 80 combinations; Pair splitting: 100 combinations; Surrender: 30 combinations) match the expected chart actions in automated unit tests.
- **SC-002**: Decision latency for the Basic Strategy Player is under 0.1 ms per turn execution, supporting high-throughput simulation benchmarking.
- **SC-003**: 100% of decisions generated by external entities (e.g., simulated Jev or Laya) can be evaluated by the Decision Comparison Service in under 0.05 ms per decision.
- **SC-004**: 100% of existing tests across the entire codebase (76/76 tests in `backend/tests/`) continue to pass without regression after replacing the mockup player.
- **SC-005**: In simulations with varying True Counts, bet sizing strictly adheres to the $1 \times \text{min\_bet}$ ($TC \leq 0$) and $N \times \text{min\_bet}$ ($TC > 0$) formula across 100% of sampled rounds.

---

## Assumptions

- **Table Rules Default**: Standard simulation rules apply (6–8 decks, Dealer stands on Soft 17 or hits Soft 17 based on `TableRules`, Double After Split allowed by default unless configured otherwise).
- **True Count Calculation**: True count is supplied in `DecisionContext` by the orchestrator/shoe using standard card counting formula ($TC = \text{Running Count} / \text{Remaining Decks}$). If not supplied or 0, TC defaults to 0.0 (minimum bet).
- **Asynchronous Protocol**: The player implements `async def get_decision(context)` to satisfy `DecisionProvider`, executing synchronously in-memory under the event loop.
- **Decoupled Comparison**: The comparison service can be invoked both synchronously during telemetry generation or as a standalone verification utility for downstream analysis.
