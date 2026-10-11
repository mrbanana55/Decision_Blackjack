"""Unit tests for Basic Strategy True Count bet sizing."""

from app.engine.card import Card, Rank, Suit
from app.models.basic_strategy_player import BasicStrategyPlayer
from app.models.decision_comparator import BetSpreadConfig


def _card(rank: Rank) -> Card:
    return Card(suit=Suit.DIAMONDS, rank=rank)


def test_bet_sizing_negative_and_neutral_count():
    """Verify bet is min_bet when True Count <= 0."""
    player = BasicStrategyPlayer(spread_config=BetSpreadConfig(min_bet=50.0, max_spread_multiplier=12))

    # TC = 0.0 -> min_bet
    assert player.get_bet(bankroll=1000.0, min_bet=50.0) == 50.0

    # TC < 0 (observed high cards -> running count negative)
    player.observe_cards([_card(Rank.TEN), _card(Rank.ACE), _card(Rank.KING)])
    assert player.counter.running_count < 0
    assert player.get_bet(bankroll=1000.0, min_bet=50.0) == 50.0


def test_bet_sizing_positive_count_proportionality():
    """Verify bet scales as n * min_bet when TC = n > 0."""
    player = BasicStrategyPlayer(spread_config=BetSpreadConfig(min_bet=50.0, max_spread_multiplier=12))

    # Force TC to +2.0 by observing low cards
    # Remaining decks in 6 decks: 312 cards. Let's feed low cards.
    # To get TC = 2 with ~5.5 decks remaining: need running count ~ +11
    player.observe_cards([_card(Rank.TWO) for _ in range(12)])
    tc = player.counter.true_count
    assert tc >= 2.0
    units = int(tc)
    expected_bet = units * 50.0
    assert player.get_bet(bankroll=2000.0, min_bet=50.0) == expected_bet


def test_bet_sizing_max_spread_cap():
    """Verify bet caps at max_spread_multiplier * min_bet."""
    player = BasicStrategyPlayer(spread_config=BetSpreadConfig(min_bet=50.0, max_spread_multiplier=12))
    # Feed 100 low cards -> enormous count
    player.observe_cards([_card(Rank.FOUR) for _ in range(100)])
    assert player.counter.true_count > 15.0

    # Max spread is 12 units -> 12 * $50 = $600
    assert player.get_bet(bankroll=2000.0, min_bet=50.0) == 600.0


def test_bet_sizing_bankroll_clamp():
    """Verify bet cannot exceed available bankroll."""
    player = BasicStrategyPlayer(spread_config=BetSpreadConfig(min_bet=50.0, max_spread_multiplier=12))
    player.observe_cards([_card(Rank.FOUR) for _ in range(50)])
    # Calculated bet is > 500, but bankroll is only 150
    assert player.get_bet(bankroll=150.0, min_bet=50.0) == 150.0


if __name__ == "__main__":
    for name, func in list(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            print(f"✓ {name}")
    print("All basic strategy betting tests passed!")
