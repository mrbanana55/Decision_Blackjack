# Interface Contract: Basic Strategy Player & Decision Comparator

**Feature**: `specs/003-basic-strategy-player/`  
**Date**: 2026-10-11  

---

## 1. `BasicStrategyPlayer` Contract

Located in `backend/app/models/basic_strategy_player.py`:

```python
class BasicStrategyPlayer:
    """Deterministic basic strategy decision provider adhering strictly to game theory."""

    def __init__(
        self,
        name: str = "OptimalStrategy",
        spread_config: BetSpreadConfig | None = None,
        rules: TableRules | None = None,
    ) -> None: ...

    @property
    def name(self) -> str: ...

    @property
    def entity_type(self) -> EntityType: ...

    def get_bet(self, bankroll: float, min_bet: float) -> float:
        """Calculate optimal opening wager based on current True Count and bet spread."""
        ...

    def reset_count(self) -> None:
        """Reset internal Hi-Lo running and true count upon shoe reshuffle/adoption."""
        ...

    def observe_card(self, card: Card) -> None:
        """Observe a single exposed card on the table and update card count."""
        ...

    async def get_decision(self, context: DecisionContext) -> AgentDecision:
        """Compute the optimal action for the current observable hand context."""
        ...
```

---

## 2. `DecisionComparator` Contract

Located in `backend/app/models/decision_comparator.py`:

```python
class DecisionComparator:
    """Evaluation oracle comparing any player's decision or bet against Basic Strategy."""

    def __init__(self, rules: TableRules | None = None, spread_config: BetSpreadConfig | None = None) -> None: ...

    def evaluate_turn_decision(
        self,
        context: DecisionContext,
        actual_action: Action,
    ) -> DecisionComparison:
        """Compare an agent's chosen action against what Basic Strategy dictates in that position."""
        ...

    def evaluate_round_bet(
        self,
        actual_bet: float,
        min_bet: float,
        true_count: float,
        bankroll: float,
    ) -> BetComparison:
        """Compare an agent's opening wager against what Basic Strategy dictates for that True Count."""
        ...
```

---

## 3. Protocol Extension: `DecisionProvider`

Updated in `backend/app/simulation/interfaces.py`:

```python
@runtime_checkable
class DecisionProvider(Protocol):
    """Abstract interface for all blackjack decision agents."""

    @property
    def name(self) -> str: ...

    @property
    def entity_type(self) -> EntityType: ...

    async def get_decision(self, context: DecisionContext) -> AgentDecision: ...

    def get_bet(self, bankroll: float, min_bet: float) -> float:
        """Optional: Determine round bet size based on bankroll and strategy."""
        ...

    def reset_count(self) -> None:
        """Optional: Reset internal count or card memory."""
        ...
```
