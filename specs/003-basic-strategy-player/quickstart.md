# Quickstart Validation Guide: Basic Strategy Player & Decision Comparator

**Feature**: `specs/003-basic-strategy-player/`  
**Date**: 2026-10-11  

---

## Scenario 1: Verify 100% Matrix Adherence Against `docs/Estrategia Optima.md`

Prove that every single hand combination produces the exact expected action.

```python
import pytest
from app.models.strategy_matrices import get_optimal_action
from app.engine.types import Action
from app.engine.rules import TableRules

def test_hard_totals():
    # 11 vs 10 -> DOUBLE (if allowed)
    action, reason = get_optimal_action(
        player_cards=[...],
        player_total=11,
        is_soft=False,
        dealer_upcard=...,
        legal_actions=[Action.HIT, Action.STAND, Action.DOUBLE],
        rules=TableRules()
    )
    assert action == Action.DOUBLE
```

---

## Scenario 2: Positional Decision Comparison for External Agent (Jev/Laya)

Demonstrate that when Jev plays 15 vs 2 and chooses Hit, the comparator detects the error (Basic Strategy stands on 15 vs 2).

```python
from app.models.decision_comparator import DecisionComparator
from app.simulation.types import DecisionContext
from app.engine.types import Action

comparator = DecisionComparator()
# Jev is holding 15 vs dealer 2, but mistakenly hits
comparison = comparator.evaluate_turn_decision(
    context=context_15_vs_2,
    actual_action=Action.HIT,
)
assert comparison.is_optimal is False
assert comparison.optimal_action == Action.STAND
assert "Stand on hard 15 vs dealer 2" in comparison.reasoning
```

---

## Scenario 3: True Count Bet Sizing Comparison

Demonstrate that when True Count is +3 with a $50 minimum bet, the expected bet is $150. If an agent wagers $50, the comparator records the delta.

```python
comparator = DecisionComparator()
bet_comp = comparator.evaluate_round_bet(
    actual_bet=50.0,
    min_bet=50.0,
    true_count=3.0,
    bankroll=1000.0,
)
assert bet_comp.is_bet_optimal is False
assert bet_comp.optimal_bet == 150.0
assert bet_comp.bet_delta == -100.0
```

---

## Scenario 4: Automated Test Execution

Run the complete test suite to ensure 100% pass rate:

```bash
uv run pytest backend/tests/ -v
```
