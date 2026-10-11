"""Unit tests for Generational Shoe Lifecycle and Session Administration (User Story 4)."""

import asyncio
from app.engine.card import Card, Rank, Suit
from app.engine.rules import TableRules
from app.engine.shoe import Shoe
from app.simulation import (
    BasicStrategyAgent,
    EventType,
    FakeJevAgent,
    SessionStatus,
    SimulationConfig,
    SimulationOrchestrator,
)


def test_generational_shoe_pool_cross_table_sharing():
    """Verify tables crossing cut-card at different times share identical shoe generations."""
    async def _test():
        # Use low-penetration single-deck shoe to trigger reshuffle quickly
        config = SimulationConfig(
            session_id="shoe-lifecycle-sim",
            seed=100,
            max_rounds=15,
            initial_bankroll=2000.0,
            table_rules=TableRules(min_bet=10.0, num_decks=1),
        )
        orchestrator = SimulationOrchestrator(config)
        # Set low penetration on shoe pool for rapid cut card triggers
        orchestrator.shoe_pool.num_decks = 1
        orchestrator.shoe_pool.penetration = 0.2  # ~10 cards until cut card

        t_opt = orchestrator.add_entity("optimal", BasicStrategyAgent())
        t_jev = orchestrator.add_entity("jev", FakeJevAgent(simulated_latency_ms=0.0))

        # Re-set table shoes to the 1-deck pool generation 0
        t_opt.adopt_shoe(orchestrator.shoe_pool.get_shoe_for_generation(0), 0)
        t_jev.adopt_shoe(orchestrator.shoe_pool.get_shoe_for_generation(0), 0)

        reshuffle_events = []
        orchestrator.event_bus.subscribe(
            EventType.SHOE_RESHUFFLED,
            lambda e: reshuffle_events.append(e),
        )

        await orchestrator.start()

        assert orchestrator.status == SessionStatus.COMPLETED
        # Verify that reshuffles occurred and generations advanced
        assert len(reshuffle_events) >= 1
        assert t_opt.shoe_generation >= 1 or t_jev.shoe_generation >= 1

        # Check that generation 1 is cached in pool
        assert orchestrator.shoe_pool.has_generation(1)

    asyncio.run(_test())


def test_all_bankrupt_triggers_early_completion():
    """Verify that when all entities are eliminated, simulation stops early with COMPLETED."""
    async def _test():
        # Set max_rounds to 100, but only $10 bankroll with $10 min bet
        config = SimulationConfig(
            session_id="bankrupt-sim",
            seed=42,
            max_rounds=100,
            initial_bankroll=10.0,
            table_rules=TableRules(min_bet=10.0),
            stop_on_all_bankrupt=True,
        )
        orchestrator = SimulationOrchestrator(config)

        # Inject losing cards so both tables lose round 1 immediately
        # Player gets 10, 6 = 16, hits, gets 10 (bust 26). Dealer gets 10, 8 = 18.
        def _make_losing_shoe():
            cards = [
                Card(Suit.HEARTS, Rank.TEN),
                Card(Suit.SPADES, Rank.TEN),
                Card(Suit.HEARTS, Rank.SIX),
                Card(Suit.SPADES, Rank.EIGHT),
                Card(Suit.CLUBS, Rank.TEN),
            ]
            return Shoe(num_decks=1, card_sequence=cards)

        t1 = orchestrator.add_entity("p1", BasicStrategyAgent())
        t2 = orchestrator.add_entity("p2", BasicStrategyAgent())

        t1.adopt_shoe(_make_losing_shoe(), 0)
        t2.adopt_shoe(_make_losing_shoe(), 0)

        eliminated_events = []
        orchestrator.event_bus.subscribe(
            EventType.ENTITY_ELIMINATED,
            lambda e: eliminated_events.append(e),
        )

        await orchestrator.start()

        assert orchestrator.status == SessionStatus.COMPLETED
        assert orchestrator.current_round == 1  # Stopped at round 1 because all bankrupt!
        assert t1.is_eliminated
        assert t2.is_eliminated
        assert len(eliminated_events) == 2

    asyncio.run(_test())


if __name__ == "__main__":
    for name, func in list(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            print(f"✓ {name}")
    print("All shoe lifecycle tests passed!")
