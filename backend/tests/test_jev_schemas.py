"""Unit tests for Jev situational schema generation.

Verifies that JevSchemaBuilder dynamically constructs TypeSafe System One requests
matching game rules, hand situations, model alias, and legal actions without hardcoded wagers or moves.
"""

from app.engine.card import Card, Rank, Suit
from app.engine.rules import TableRules
from app.engine.types import Action, SurrenderRule
from app.integrations.jev.builder import JevSchemaBuilder
from app.integrations.jev.schemas import HandSituationType
from app.simulation.types import DecisionContext


def test_initial_paired_hand_surrender_disabled():
    """Verify Contract 1A: Paired hand with split available, surrender disabled."""
    builder = JevSchemaBuilder()
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
    assert req.model == "jev-latest"
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
    builder = JevSchemaBuilder()
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
    builder = JevSchemaBuilder()
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
    builder = JevSchemaBuilder()
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

    req = builder.build_hand_decision_request(context=context, rules=rules, bankroll=1200.0)
    action_q = req.questions["action"]
    assert "double" in action_q.criteria
    assert "surrender" in action_q.criteria
    assert "hit" in action_q.criteria
    assert "stand" in action_q.criteria


def test_multi_card_hand_excludes_split_double_surrender():
    """Verify Contract 3: Post-hit hand (3+ cards) restricts choices strictly to hit and stand."""
    builder = JevSchemaBuilder()
    rules = TableRules(surrender_rule=SurrenderRule.LATE, min_bet=50.0)
    context = DecisionContext(
        session_id="test-sim-1",
        round_number=20,
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

    req = builder.build_hand_decision_request(context=context, rules=rules, bankroll=950.0)
    action_q = req.questions["action"]
    assert set(action_q.criteria.keys()) == {"hit", "stand"}
    assert "split" not in action_q.criteria
    assert "double" not in action_q.criteria
    assert "surrender" not in action_q.criteria


def test_detect_hand_situation():
    """Verify situation categorization logic."""
    builder = JevSchemaBuilder()

    # Pair with split
    c_split = DecisionContext(
        session_id="s",
        round_number=1,
        hand_index=0,
        player_cards=[Card(Suit.SPADES, Rank.EIGHT), Card(Suit.DIAMONDS, Rank.EIGHT)],
        player_total=16,
        is_soft=False,
        dealer_upcard=Card(Suit.HEARTS, Rank.SEVEN),
        legal_actions=[Action.HIT, Action.STAND, Action.SPLIT],
    )
    assert builder.detect_hand_situation(c_split) == HandSituationType.INITIAL_PAIR_SPLIT

    # Standard 2-card
    c_std = DecisionContext(
        session_id="s",
        round_number=1,
        hand_index=0,
        player_cards=[Card(Suit.SPADES, Rank.TEN), Card(Suit.DIAMONDS, Rank.SIX)],
        player_total=16,
        is_soft=False,
        dealer_upcard=Card(Suit.HEARTS, Rank.SEVEN),
        legal_actions=[Action.HIT, Action.STAND],
    )
    assert builder.detect_hand_situation(c_std) == HandSituationType.INITIAL_STANDARD

    # 3-card multi-draw
    c_multi = DecisionContext(
        session_id="s",
        round_number=1,
        hand_index=0,
        player_cards=[
            Card(Suit.SPADES, Rank.FIVE),
            Card(Suit.DIAMONDS, Rank.SIX),
            Card(Suit.CLUBS, Rank.TWO),
        ],
        player_total=13,
        is_soft=False,
        dealer_upcard=Card(Suit.HEARTS, Rank.SEVEN),
        legal_actions=[Action.HIT, Action.STAND],
    )
    assert builder.detect_hand_situation(c_multi) == HandSituationType.MULTI_CARD_DRAW


def test_insurance_request_schema():
    """Verify Situation 4: Insurance offer contract when dealer reveals an Ace."""
    builder = JevSchemaBuilder()
    context = DecisionContext(
        session_id="test-sim-insurance",
        round_number=8,
        hand_index=0,
        player_cards=[Card(Suit.SPADES, Rank.KING), Card(Suit.DIAMONDS, Rank.SEVEN)],
        player_total=17,
        is_soft=False,
        dealer_upcard=Card(Suit.HEARTS, Rank.ACE),
        legal_actions=[],
        can_insure=True,
        true_count=3.0,
    )

    req = builder.build_insurance_request(
        context=context, insurance_cost=25.0, bankroll=1000.0, model="jev-latest"
    )
    assert req.model == "jev-latest"
    assert "insurance" in req.questions
    ins_q = req.questions["insurance"]
    assert ins_q.type == "choice"
    assert "accept" in ins_q.criteria
    assert "decline" in ins_q.criteria
    assert "$25.00" in ins_q.criteria["accept"]
    assert "Dealer exposed upcard is Ace" in req.state


def test_round_betting_request_schema():
    """Verify Situation 5: Pre-deal wager sizing with discrete multipliers scaling by min_bet."""
    builder = JevSchemaBuilder()
    rules = TableRules(min_bet=25.0)

    # Plentiful bankroll ($1000)
    req = builder.build_betting_request(
        bankroll=1000.0,
        rules=rules,
        true_count=2.5,
        cards_seen=140,
        total_cards=312,
        round_number=14,
        model="jev-latest",
    )
    assert req.model == "jev-latest"
    assert "bet_sizing" in req.questions
    bet_q = req.questions["bet_sizing"]
    assert bet_q.type == "choice"
    assert "1x" in bet_q.criteria
    assert "2x" in bet_q.criteria
    assert "4x" in bet_q.criteria
    assert "8x" in bet_q.criteria
    assert "$25.00" in bet_q.criteria["1x"]
    assert "$50.00" in bet_q.criteria["2x"]
    assert "$100.00" in bet_q.criteria["4x"]
    assert "$200.00" in bet_q.criteria["8x"]

    # Low bankroll ($30)
    req_low = builder.build_betting_request(
        bankroll=30.0,
        rules=rules,
        true_count=0.0,
        model="jev-latest",
    )
    bet_q_low = req_low.questions["bet_sizing"]
    assert "1x" in bet_q_low.criteria
    assert "2x" not in bet_q_low.criteria
    assert "min" in bet_q_low.criteria
