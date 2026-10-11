"""Unit tests for BasicStrategyPlayer in backend/app/models/basic_strategy_player.py."""

import asyncio
from app.engine.card import Card, Rank, Suit
from app.engine.rules import TableRules
from app.engine.types import Action
from app.models.basic_strategy_player import BasicStrategyPlayer
from app.simulation.interfaces import DecisionProvider
from app.simulation.types import DecisionContext, EntityType


def _card(rank: Rank) -> Card:
    return Card(suit=Suit.CLUBS, rank=rank)


def _make_context(
    player_cards: list[Card],
    dealer_upcard: Card,
    legal_actions: list[Action],
    player_total: int,
    is_soft: bool,
    can_insure: bool = False,
    true_count: float = 0.0,
) -> DecisionContext:
    return DecisionContext(
        session_id="test-sim",
        round_number=1,
        hand_index=0,
        player_cards=player_cards,
        player_total=player_total,
        is_soft=is_soft,
        dealer_upcard=dealer_upcard,
        legal_actions=legal_actions,
        can_insure=can_insure,
        true_count=true_count,
    )


def test_player_protocol_compliance():
    """Verify player conforms to DecisionProvider."""
    player = BasicStrategyPlayer(name="OptimalPlayer")
    assert isinstance(player, DecisionProvider)
    assert player.name == "OptimalPlayer"
    assert player.entity_type == EntityType.OPTIMAL


def test_player_hard_totals():
    """Verify player decisions on hard totals."""
    player = BasicStrategyPlayer()

    async def _run():
        # Hard 11 vs 6 -> Double
        ctx1 = _make_context(
            player_cards=[_card(Rank.FIVE), _card(Rank.SIX)],
            dealer_upcard=_card(Rank.SIX),
            legal_actions=[Action.HIT, Action.STAND, Action.DOUBLE],
            player_total=11,
            is_soft=False,
        )
        dec1 = await player.get_decision(ctx1)
        assert dec1.action == Action.DOUBLE
        assert dec1.confidence == 1.0

        # Hard 11 vs 6 when Double is illegal -> Hit
        ctx2 = _make_context(
            player_cards=[_card(Rank.FIVE), _card(Rank.THREE), _card(Rank.THREE)],
            dealer_upcard=_card(Rank.SIX),
            legal_actions=[Action.HIT, Action.STAND],
            player_total=11,
            is_soft=False,
        )
        dec2 = await player.get_decision(ctx2)
        assert dec2.action == Action.HIT

    asyncio.run(_run())


def test_player_soft_totals_and_doubling_fallbacks():
    """Verify player soft totals and Ds fallback."""
    player = BasicStrategyPlayer()

    async def _run():
        # Soft 18 (A,7) vs 3: Ds -> Double if legal
        ctx1 = _make_context(
            player_cards=[_card(Rank.ACE), _card(Rank.SEVEN)],
            dealer_upcard=_card(Rank.THREE),
            legal_actions=[Action.HIT, Action.STAND, Action.DOUBLE],
            player_total=18,
            is_soft=True,
        )
        dec1 = await player.get_decision(ctx1)
        assert dec1.action == Action.DOUBLE

        # Soft 18 (A,7) vs 3: Ds -> Stand if Double is illegal
        ctx2 = _make_context(
            player_cards=[_card(Rank.ACE), _card(Rank.FIVE), _card(Rank.TWO)],
            dealer_upcard=_card(Rank.THREE),
            legal_actions=[Action.HIT, Action.STAND],
            player_total=18,
            is_soft=True,
        )
        dec2 = await player.get_decision(ctx2)
        assert dec2.action == Action.STAND

    asyncio.run(_run())


def test_player_pair_splitting_and_surrender():
    """Verify pair splitting and surrender handling."""
    rules = TableRules(double_after_split=True, surrender_rule="late")
    player = BasicStrategyPlayer(rules=rules)

    async def _run():
        # Pair of 8s vs 9 -> Split
        ctx1 = _make_context(
            player_cards=[_card(Rank.EIGHT), _card(Rank.EIGHT)],
            dealer_upcard=_card(Rank.NINE),
            legal_actions=[Action.HIT, Action.STAND, Action.SPLIT],
            player_total=16,
            is_soft=False,
        )
        dec1 = await player.get_decision(ctx1)
        assert dec1.action == Action.SPLIT

        # Hard 16 vs 10 -> Surrender
        ctx2 = _make_context(
            player_cards=[_card(Rank.TEN), _card(Rank.SIX)],
            dealer_upcard=_card(Rank.TEN),
            legal_actions=[Action.HIT, Action.STAND, Action.SURRENDER],
            player_total=16,
            is_soft=False,
        )
        dec2 = await player.get_decision(ctx2)
        assert dec2.action == Action.SURRENDER

    asyncio.run(_run())


def test_player_insurance_rejection():
    """Verify insurance is always declined ("DON'T TAKE")."""
    player = BasicStrategyPlayer()

    async def _run():
        # Even when can_insure=True or insurance is offered, player doesn't accept
        ctx = _make_context(
            player_cards=[_card(Rank.TEN), _card(Rank.TEN)],
            dealer_upcard=_card(Rank.ACE),
            legal_actions=[Action.STAND, Action.HIT],
            player_total=20,
            is_soft=False,
            can_insure=True,
        )
        dec = await player.get_decision(ctx)
        # Decision should be STAND (never insurance action)
        assert dec.action == Action.STAND

    asyncio.run(_run())


if __name__ == "__main__":
    for name, func in list(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            print(f"✓ {name}")
    print("All basic strategy player tests passed!")
