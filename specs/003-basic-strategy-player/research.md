# Research & Architecture Decisions: Basic Strategy Player & Comparison Oracle

**Feature**: `specs/003-basic-strategy-player/`  
**Date**: 2026-10-11  

---

## 1. Architectural Placement: `backend/app/models/` vs `backend/app/simulation/`

### Context & User Request
The user specified: `Create this inside @[backend/app/models]`.
We need to determine the clean separation of concerns between:
1. Pure mathematical Strategy Matrix tables, Card Counter, and Decision Comparator entities.
2. The `DecisionProvider` agent implementation (`BasicStrategyAgent` / `BasicStrategyPlayer`).
3. The orchestration telemetry and table integration.

### Decision
We organize the core strategy logic, counting models, matrices, and comparison oracle inside `backend/app/models/` (and export/connect cleanly where needed):
- `backend/app/models/strategy_matrices.py`: Strict representations of Hard Totals, Soft Totals, Pair Splitting (DAS-aware), and Surrender lookup matrices as specified in `docs/Estrategia Optima.md`.
- `backend/app/models/card_counter.py`: Hi-Lo Running Count & True Count tracker (`HiLoCardCounter`) with deck estimation and `reset()`.
- `backend/app/models/decision_comparator.py`: Standalone comparison oracle (`DecisionComparator`, `DecisionComparison`, `BetComparison`) providing positional hand evaluations and bet spread comparisons.
- `backend/app/models/basic_strategy_player.py`: The concrete player (`BasicStrategyPlayer`) utilizing the matrices, card counter, and bet spread rules to implement the `DecisionProvider` protocol.
- `backend/app/simulation/agents/basic_strategy.py`: Backward-compatible alias/export of `BasicStrategyPlayer` as `BasicStrategyAgent`, ensuring 100% compatibility with existing imports and tests.

### Rationale
- Keeps `backend/app/models/` as the home of core decision models (including future Jev/Laya adapters or evaluation models).
- Strategy logic and matrix evaluation become pure, reusable models that can be called from anywhere without coupling to the simulation loop.
- Guarantees zero regression on existing orchestrator tests that import `from app.simulation.agents.basic_strategy import BasicStrategyAgent`.

---

## 2. Strict Matrix Lookup vs Procedural Rules

### Decision
Use immutable, typed dictionary lookups (`StrategyMatrix`) keyed by `(player_state, dealer_upcard_value)` with explicit action priorities:
1. Surrender Check (if 16 vs 9,10,A or 15 vs 10, 2-card hand, legal).
2. Pair Splitting Check (if 2 cards of same rank/nominal value, checking DAS rules for `Y/N`).
3. Soft Totals Check (if soft hand total $\le 21$, evaluating `Ds` as Double if legal, else Stand).
4. Hard Totals Check (if hard hand total, evaluating `D` as Double if legal, else Hit).

### Rationale
- `docs/Estrategia Optima.md` explicitly lists 100 cells for Hard Totals, 80 for Soft Totals, 100 for Pair Splitting, and 30 for Surrender.
- Table-driven dictionary lookup eliminates "if/else" heuristics, ensures every single cell in the documentation is verified by tests, and prevents any "guessing" by the player.

---

## 3. Positional Contextual Comparison Oracle

### Decision
The `DecisionComparator` evaluates other agents (Jev, Laya) **strictly in their observed table position**:
- For a turn action: Given a player's `hand` and the `dealer_upcard` and `legal_actions` from `DecisionContext`, the comparator invokes the matrix lookup for that specific combination. It returns:
  - `is_optimal`: `actual_action == optimal_action`
  - `optimal_action`: The exact action dictated by the chart
  - `actual_action`: What the agent chose
  - `category`: `HARD_TOTAL`, `SOFT_TOTAL`, `PAIR_SPLIT`, `SURRENDER`, `INSURANCE`
  - `reasoning`: Rule explanation from the chart (e.g. "Basic strategy stands on hard 15 vs dealer 2-6")
- For an opening bet: Given the table's prevailing `true_count`, `minimum_bet`, and `bankroll`, the comparator computes the expected bet:
  - If $TC \le 0 \rightarrow 1 \times \text{min\_bet}$
  - If $TC > 0 \rightarrow \min(\lfloor TC \rfloor, \text{max\_spread}) \times \text{min\_bet}$
  - It compares against the actual placed bet, computing `is_bet_optimal: bool` and `bet_delta = actual_bet - optimal_bet`.

### Rationale
Directly fulfills the user's requirement: even when Jev has 15 vs 2 while Basic Strategy has 12 vs 5, Jev is benchmarked against what Basic Strategy would do with 15 vs 2.

---

## 4. Hi-Lo Card Counting & Bet Sizing

### Decision
`HiLoCardCounter`:
- Values: 2, 3, 4, 5, 6 $\rightarrow +1$; 7, 8, 9 $\rightarrow 0$; 10, J, Q, K, A $\rightarrow -1$.
- Running Count: $\sum \text{card values}$.
- Remaining Decks: $\max(0.5, \text{round}((\text{total\_cards} - \text{cards\_seen}) / 52.0, 1))$.
- True Count: $\text{round}(\text{Running Count} / \text{Remaining Decks}, 1)$.
- Bet Sizing: Table min bet when $TC \le 0$; $TC \times \text{min\_bet}$ (capped at 12 units) when $TC > 0$. Bankroll capped.
- Reset: Invoked upon shoe reset or adoption of a new generation shoe.
