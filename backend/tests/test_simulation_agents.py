"""Unit tests for agent providers (BasicStrategyAgent, FakeJevAgent, FakeLayaAgent)."""

import asyncio
import time
from app.engine.card import Card, Rank, Suit
from app.engine.types import Action
from app.simulation.agents.basic_strategy import BasicStrategyAgent
from app.simulation.agents.fake_agents import FakeJevAgent, FakeLayaAgent
from app.simulation.interfaces import AgentFaultError, DecisionProvider
from app.simulation.types import DecisionContext, EntityType


def _make_context(
    player_cards: list[Card],
    dealer_upcard: Card,
    legal_actions: list[Action],
    player_total: int,
    is_soft: bool,
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
    )


def test_basic_strategy_conforms_to_protocol():
    agent = BasicStrategyAgent()
    assert isinstance(agent, DecisionProvider)
    assert agent.entity_type == EntityType.OPTIMAL


def test_basic_strategy_hard_totals():
    async def _test():
        agent = BasicStrategyAgent()

        # Hard 16 vs dealer 10 -> HIT
        c_16_vs_10 = _make_context(
            player_cards=[Card(Suit.HEARTS, Rank.TEN), Card(Suit.SPADES, Rank.SIX)],
            dealer_upcard=Card(Suit.CLUBS, Rank.TEN),
            legal_actions=[Action.HIT, Action.STAND],
            player_total=16,
            is_soft=False,
        )
        dec = await agent.get_decision(c_16_vs_10)
        assert dec.action == Action.HIT
        assert dec.confidence == 1.0

        # Hard 16 vs dealer 5 -> STAND
        c_16_vs_5 = _make_context(
            player_cards=[Card(Suit.HEARTS, Rank.TEN), Card(Suit.SPADES, Rank.SIX)],
            dealer_upcard=Card(Suit.CLUBS, Rank.FIVE),
            legal_actions=[Action.HIT, Action.STAND],
            player_total=16,
            is_soft=False,
        )
        dec2 = await agent.get_decision(c_16_vs_5)
        assert dec2.action == Action.STAND

    asyncio.run(_test())


def test_basic_strategy_splitting_and_doubling():
    async def _test():
        agent = BasicStrategyAgent()

        # 8,8 vs dealer 9 -> SPLIT (Y)
        c_split = _make_context(
            player_cards=[Card(Suit.HEARTS, Rank.EIGHT), Card(Suit.SPADES, Rank.EIGHT)],
            dealer_upcard=Card(Suit.CLUBS, Rank.NINE),
            legal_actions=[Action.HIT, Action.STAND, Action.SPLIT],
            player_total=16,
            is_soft=False,
        )
        dec = await agent.get_decision(c_split)
        assert dec.action == Action.SPLIT

        # 8,8 vs dealer 10 -> NO SPLIT (N in docs/Estrategia Optima.md), hard 16 vs 10 -> HIT
        c_no_split = _make_context(
            player_cards=[Card(Suit.HEARTS, Rank.EIGHT), Card(Suit.SPADES, Rank.EIGHT)],
            dealer_upcard=Card(Suit.CLUBS, Rank.TEN),
            legal_actions=[Action.HIT, Action.STAND, Action.SPLIT],
            player_total=16,
            is_soft=False,
        )
        dec_no_split = await agent.get_decision(c_no_split)
        assert dec_no_split.action == Action.HIT

        # Hard 11 vs dealer 6 -> DOUBLE
        c_double = _make_context(
            player_cards=[Card(Suit.HEARTS, Rank.SIX), Card(Suit.SPADES, Rank.FIVE)],
            dealer_upcard=Card(Suit.CLUBS, Rank.SIX),
            legal_actions=[Action.HIT, Action.STAND, Action.DOUBLE],
            player_total=11,
            is_soft=False,
        )
        dec2 = await agent.get_decision(c_double)
        assert dec2.action == Action.DOUBLE

        # If DOUBLE is illegal, fall back to HIT
        c_double_illegal = _make_context(
            player_cards=[Card(Suit.HEARTS, Rank.SIX), Card(Suit.SPADES, Rank.FIVE)],
            dealer_upcard=Card(Suit.CLUBS, Rank.SIX),
            legal_actions=[Action.HIT, Action.STAND],  # No DOUBLE
            player_total=11,
            is_soft=False,
        )
        dec3 = await agent.get_decision(c_double_illegal)
        assert dec3.action == Action.HIT

    asyncio.run(_test())


def test_fake_jev_agent():
    async def _test():
        jev = FakeJevAgent(simulated_latency_ms=10.0, confidence=0.85)
        assert isinstance(jev, DecisionProvider)
        assert jev.entity_type == EntityType.JEV

        ctx = _make_context(
            player_cards=[Card(Suit.HEARTS, Rank.TEN), Card(Suit.SPADES, Rank.EIGHT)],
            dealer_upcard=Card(Suit.CLUBS, Rank.SIX),
            legal_actions=[Action.HIT, Action.STAND],
            player_total=18,
            is_soft=False,
        )

        t0 = time.perf_counter()
        dec = await jev.get_decision(ctx)
        elapsed = (time.perf_counter() - t0) * 1000.0

        assert dec.action == Action.STAND
        assert dec.confidence == 0.85
        assert elapsed >= 8.0  # Approx latency simulated
        assert "Jev" in dec.reasoning

        # Test fault injection
        jev.inject_fault()
        fault_raised = False
        try:
            await jev.get_decision(ctx)
        except AgentFaultError:
            fault_raised = True
        assert fault_raised

        # Test illegal action injection
        jev.inject_illegal_action()
        dec_illegal = await jev.get_decision(ctx)
        assert dec_illegal.action not in ctx.legal_actions

    asyncio.run(_test())


def test_fake_laya_agent():
    async def _test():
        laya = FakeLayaAgent(simulated_latency_ms=5.0, confidence=0.95)
        assert isinstance(laya, DecisionProvider)
        assert laya.entity_type == EntityType.LAYA

        ctx = _make_context(
            player_cards=[Card(Suit.HEARTS, Rank.TEN), Card(Suit.SPADES, Rank.SIX)],
            dealer_upcard=Card(Suit.CLUBS, Rank.SEVEN),
            legal_actions=[Action.HIT, Action.STAND],
            player_total=16,
            is_soft=False,
        )

        dec = await laya.get_decision(ctx)
        assert dec.action == Action.HIT
        assert dec.confidence == 0.95
        assert "Laya" in dec.reasoning

        # Test fault injection
        laya.inject_fault()
        fault_raised = False
        try:
            await laya.get_decision(ctx)
        except AgentFaultError:
            fault_raised = True
        assert fault_raised

    asyncio.run(_test())


if __name__ == "__main__":
    for name, func in list(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            print(f"✓ {name}")
    print("All agent tests passed!")
