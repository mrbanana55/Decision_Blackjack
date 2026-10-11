"""Unit tests for EntityTable."""

import asyncio
from app.engine.card import Card, Rank, Suit
from app.engine.rules import TableRules
from app.engine.shoe import Shoe
from app.engine.types import Action, RoundPhase
from app.simulation.agents.basic_strategy import BasicStrategyAgent
from app.simulation.agents.fake_agents import FakeJevAgent
from app.simulation.interfaces import IllegalAgentActionError
from app.simulation.table import EntityTable


def test_table_initialization_and_metrics():
    agent = BasicStrategyAgent()
    table = EntityTable(entity_id="test-optimal", provider=agent, initial_bankroll=1000.0)

    assert table.entity_id == "test-optimal"
    assert table.current_bankroll == 1000.0
    assert table.shoe_generation == 0
    assert not table.is_eliminated

    m = table.metrics
    assert m.starting_bankroll == 1000.0
    assert m.current_bankroll == 1000.0
    assert m.rounds_played == 0
    assert m.net_profit == 0.0


def test_table_round_execution():
    async def _test():
        agent = BasicStrategyAgent()
        rules = TableRules(min_bet=10.0, max_bet=500.0)
        # Create seeded shoe
        shoe = Shoe(num_decks=6, seed=42)
        table = EntityTable(
            entity_id="test-table",
            provider=agent,
            rules=rules,
            shoe=shoe,
            initial_bankroll=1000.0,
        )

        settlement = await table.step_round_to_completion(bet=25.0, session_id="sim-1", round_number=1)
        assert settlement is not None
        assert table.rounds_played == 1
        assert table.current_bankroll == settlement.final_bankroll
        assert table.metrics.rounds_played == 1

    asyncio.run(_test())


def test_table_catches_illegal_action():
    async def _test():
        agent = FakeJevAgent(simulated_latency_ms=0.0)
        # Inject cards: Player gets 10, 6; Dealer gets 7, 8 -> Player turns
        cards = [
            Card(Suit.HEARTS, Rank.TEN),   # Player
            Card(Suit.SPADES, Rank.SEVEN), # Dealer upcard
            Card(Suit.HEARTS, Rank.SIX),   # Player
            Card(Suit.SPADES, Rank.EIGHT), # Dealer hole card
        ]
        shoe = Shoe(num_decks=1, card_sequence=cards)
        table = EntityTable(entity_id="jev", provider=agent, shoe=shoe, initial_bankroll=500.0)

        # Force next action to be illegal
        agent.inject_illegal_action()

        table.start_round(bet=20.0)
        assert table.phase == RoundPhase.PLAYER_TURNS
        raised = False
        try:
            await table.play_turn()
        except IllegalAgentActionError:
            raised = True
        assert raised

    asyncio.run(_test())


def test_adopt_shoe():
    agent = BasicStrategyAgent()
    table = EntityTable(entity_id="opt", provider=agent)
    assert table.shoe_generation == 0

    new_shoe = Shoe(num_decks=6, seed=999)
    table.adopt_shoe(new_shoe, generation=1)

    assert table.shoe_generation == 1
    assert table.round_engine.shoe == new_shoe


def test_bankruptcy_elimination():
    agent = BasicStrategyAgent()
    rules = TableRules(min_bet=100.0)
    # Start with 100 bankroll
    table = EntityTable(entity_id="broke", provider=agent, rules=rules, initial_bankroll=100.0)

    # Inject cards:
    # Player gets 10, 6 = 16. Dealer gets 7, 8 = 15.
    # Player hits 16 vs 7, draws 10, busts with 26!
    # Dealer wins, player bankroll remains 0.0.
    injected = [
        Card(Suit.HEARTS, Rank.TEN),   # Player 1
        Card(Suit.SPADES, Rank.SEVEN), # Dealer upcard
        Card(Suit.HEARTS, Rank.SIX),   # Player 2
        Card(Suit.SPADES, Rank.EIGHT), # Dealer hole card
        Card(Suit.CLUBS, Rank.TEN),    # Player hits and busts (26)
    ]
    table.round_engine.shoe = Shoe(num_decks=1, card_sequence=injected)

    async def _test():
        await table.step_round_to_completion(bet=100.0)
        assert table.current_bankroll == 0.0
        assert table.is_eliminated

    asyncio.run(_test())


if __name__ == "__main__":
    for name, func in list(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            print(f"✓ {name}")
    print("All entity table tests passed!")
