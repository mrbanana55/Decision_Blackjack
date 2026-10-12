"""Unit tests for Laya situational schema generation.

Verifies that LayaSchemaBuilder dynamically constructs TypeSafe System One requests
matching game rules, hand situations, and legal actions without hardcoded wagers or moves.
"""

from app.engine.card import Card, Rank, Suit
from app.engine.rules import TableRules
from app.engine.types import Action, SurrenderRule
from app.integrations.laya.builder import LayaSchemaBuilder
from app.integrations.laya.schemas import HandSituationType
from app.simulation.types import DecisionContext


def test_initial_paired_hand_surrender_disabled():
    """Verify Contract 1A: Paired hand with split available, surrender disabled."""
    builder = LayaSchemaBuilder()
    rules = TableRules(surrender_rule=SurrenderRule.NONE, min_bet=50.0)
    context = DecisionContext(
        session_id="test-sim-1",
        round_number=5,
        hand_index=0,
        player_cards=[Card(Suit.SPADES, Rank.EIGHT), Card(Suit.DIAMONDS, Rank.EIGHT)],
        player_total=16,
        is_soft=False,
        dealer_upcard=Card(Suit.HEARTS, Rank.SEVEN),
        legal_actions=[Action.HIT, Action.STAND, Action.SPLIT],
        true_count=0.5,
    )

    req = builder.build_hand_decision_request(context=context, rules=rules, bankroll=1000.0)
    assert req.state is not None
    assert "Pair of 8" in req.state or "8 of Spades, 8 of Diamonds" in req.state
    assert "action" in req.questions

    action_q = req.questions["action"]
    assert action_q.type == "choice"
    assert "split" in action_q.criteria
    assert "hit" in action_q.criteria
    assert "stand" in action_q.criteria
    assert "surrender" not in action_q.criteria
    assert "double" not in action_q.criteria


def test_initial_paired_hand_surrender_enabled():
    """Verify Contract 1B: Paired hand with split and surrender available."""
    builder = LayaSchemaBuilder()
    rules = TableRules(surrender_rule=SurrenderRule.LATE, min_bet=50.0)
    context = DecisionContext(
        session_id="test-sim-1",
        round_number=7,
        hand_index=0,
        player_cards=[Card(Suit.SPADES, Rank.EIGHT), Card(Suit.DIAMONDS, Rank.EIGHT)],
        player_total=16,
        is_soft=False,
        dealer_upcard=Card(Suit.CLUBS, Rank.TEN),
        legal_actions=[Action.HIT, Action.STAND, Action.SPLIT, Action.SURRENDER],
        true_count=0.0,
    )

    req = builder.build_hand_decision_request(context=context, rules=rules, bankroll=1000.0)
    action_q = req.questions["action"]
    assert "split" in action_q.criteria
    assert "surrender" in action_q.criteria
    assert "hit" in action_q.criteria
    assert "stand" in action_q.criteria


def test_initial_standard_hand_surrender_disabled():
    """Verify Contract 2A: 2-card non-paired hand with double, surrender disabled."""
    builder = LayaSchemaBuilder()
    rules = TableRules(surrender_rule=SurrenderRule.NONE, min_bet=50.0)
    context = DecisionContext(
        session_id="test-sim-1",
        round_number=12,
        hand_index=0,
        player_cards=[Card(Suit.DIAMONDS, Rank.FIVE), Card(Suit.CLUBS, Rank.SIX)],
        player_total=11,
        is_soft=False,
        dealer_upcard=Card(Suit.SPADES, Rank.SIX),
        legal_actions=[Action.HIT, Action.STAND, Action.DOUBLE],
        true_count=2.0,
    )

    req = builder.build_hand_decision_request(context=context, rules=rules, bankroll=850.0)
    action_q = req.questions["action"]
    assert "double" in action_q.criteria
    assert "hit" in action_q.criteria
    assert "stand" in action_q.criteria
    assert "split" not in action_q.criteria
    assert "surrender" not in action_q.criteria


def test_initial_standard_hand_surrender_enabled():
    """Verify Contract 2B: 2-card non-paired hand with double and surrender available."""
    builder = LayaSchemaBuilder()
    rules = TableRules(surrender_rule=SurrenderRule.LATE, min_bet=50.0)
    context = DecisionContext(
        session_id="test-sim-1",
        round_number=15,
        hand_index=0,
        player_cards=[Card(Suit.SPADES, Rank.TEN), Card(Suit.HEARTS, Rank.SIX)],
        player_total=16,
        is_soft=False,
        dealer_upcard=Card(Suit.CLUBS, Rank.TEN),
        legal_actions=[Action.HIT, Action.STAND, Action.DOUBLE, Action.SURRENDER],
        true_count=1.0,
    )

    req = builder.build_hand_decision_request(context=context, rules=rules, bankroll=950.0)
    action_q = req.questions["action"]
    assert "double" in action_q.criteria
    assert "surrender" in action_q.criteria
    assert "hit" in action_q.criteria
    assert "stand" in action_q.criteria
    assert "split" not in action_q.criteria


def test_multi_card_draw_hand_excludes_double_split_surrender():
    """Verify Contract 3: Multi-card hand (3+ cards) strictly limits criteria to hit and stand."""
    builder = LayaSchemaBuilder()
    rules = TableRules(surrender_rule=SurrenderRule.LATE, min_bet=50.0)
    context = DecisionContext(
        session_id="test-sim-1",
        round_number=12,
        hand_index=0,
        player_cards=[
            Card(Suit.SPADES, Rank.TEN),
            Card(Suit.HEARTS, Rank.THREE),
            Card(Suit.CLUBS, Rank.THREE),
        ],
        player_total=16,
        is_soft=False,
        dealer_upcard=Card(Suit.CLUBS, Rank.TEN),
        legal_actions=[Action.HIT, Action.STAND],
        true_count=1.5,
    )

    req = builder.build_hand_decision_request(context=context, rules=rules, bankroll=800.0)
    action_q = req.questions["action"]
    assert set(action_q.criteria.keys()) == {"hit", "stand"}
    assert "double" not in action_q.criteria
    assert "split" not in action_q.criteria
    assert "surrender" not in action_q.criteria


def test_situation_detector_classifications():
    """Verify HandSituationType detection logic across table states."""
    builder = LayaSchemaBuilder()

    # Paired
    c_pair = DecisionContext(
        session_id="s1", round_number=1, hand_index=0,
        player_cards=[Card(Suit.HEARTS, Rank.EIGHT), Card(Suit.CLUBS, Rank.EIGHT)],
        player_total=16, is_soft=False, dealer_upcard=Card(Suit.SPADES, Rank.TEN),
        legal_actions=[Action.HIT, Action.STAND, Action.SPLIT],
    )
    assert builder.detect_hand_situation(c_pair) == HandSituationType.INITIAL_PAIR_SPLIT

    # Standard 2-card
    c_std = DecisionContext(
        session_id="s1", round_number=1, hand_index=0,
        player_cards=[Card(Suit.HEARTS, Rank.TEN), Card(Suit.CLUBS, Rank.SIX)],
        player_total=16, is_soft=False, dealer_upcard=Card(Suit.SPADES, Rank.TEN),
        legal_actions=[Action.HIT, Action.STAND, Action.DOUBLE],
    )
    assert builder.detect_hand_situation(c_std) == HandSituationType.INITIAL_STANDARD

    # 3-card
    c_multi = DecisionContext(
        session_id="s1", round_number=1, hand_index=0,
        player_cards=[Card(Suit.HEARTS, Rank.TEN), Card(Suit.CLUBS, Rank.TWO), Card(Suit.SPADES, Rank.FOUR)],
        player_total=16, is_soft=False, dealer_upcard=Card(Suit.SPADES, Rank.TEN),
        legal_actions=[Action.HIT, Action.STAND],
    )
    assert builder.detect_hand_situation(c_multi) == HandSituationType.MULTI_CARD_DRAW


def test_insurance_request_schema_situation_4():
    """Verify Contract 4: Insurance offer schema format and criteria."""
    builder = LayaSchemaBuilder()
    context = DecisionContext(
        session_id="test-sim-ins",
        round_number=3,
        hand_index=0,
        player_cards=[Card(Suit.SPADES, Rank.TEN), Card(Suit.HEARTS, Rank.EIGHT)],
        player_total=18,
        is_soft=False,
        dealer_upcard=Card(Suit.CLUBS, Rank.ACE),
        legal_actions=[Action.HIT, Action.STAND],
        true_count=2.0,
    )

    req = builder.build_insurance_request(context=context, insurance_cost=25.0, bankroll=975.0)

    assert "insurance" in req.questions
    q = req.questions["insurance"]
    assert q.type == "choice"
    assert "accept" in q.criteria
    assert "decline" in q.criteria
    assert "$25.00" in q.criteria["accept"]
    assert "Dealer exposed upcard is Ace" in req.state
    assert "$975.00" in req.state


def test_betting_request_schema_situation_5_dynamic_min_bet():
    """Verify Contract 5: Pre-deal betting wager schema with dynamic table minimum bet."""
    builder = LayaSchemaBuilder()

    # Case 1: Custom min_bet = $100, bankroll = $2,000
    rules_100 = TableRules(min_bet=100.0)
    req_100 = builder.build_betting_request(
        bankroll=2000.0,
        rules=rules_100,
        true_count=3.0,
        cards_seen=150,
        total_cards=312,
        round_number=8,
    )

    assert "bet_sizing" in req_100.questions
    q_100 = req_100.questions["bet_sizing"]
    assert q_100.type == "choice"
    assert "1x" in q_100.criteria and "$100.00" in q_100.criteria["1x"]
    assert "2x" in q_100.criteria and "$200.00" in q_100.criteria["2x"]
    assert "4x" in q_100.criteria and "$400.00" in q_100.criteria["4x"]
    assert "8x" in q_100.criteria and "$800.00" in q_100.criteria["8x"]
    assert "Table Rules Minimum Bet: $100.00" in req_100.state
    assert "+3.0" in req_100.state

    # Case 2: Custom min_bet = $25, bankroll = $50 (only 1x and 2x affordable)
    rules_25 = TableRules(min_bet=25.0)
    req_25 = builder.build_betting_request(
        bankroll=50.0,
        rules=rules_25,
        true_count=0.0,
    )
    q_25 = req_25.questions["bet_sizing"]
    assert "1x" in q_25.criteria and "$25.00" in q_25.criteria["1x"]
    assert "2x" in q_25.criteria and "$50.00" in q_25.criteria["2x"]
    assert "4x" not in q_25.criteria  # 4x ($100) > $50 bankroll
    assert "8x" not in q_25.criteria
