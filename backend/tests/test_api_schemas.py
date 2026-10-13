"""Unit tests for API request/response schemas and table rules validation."""

import pytest
from pydantic import ValidationError

from app.api.schemas import (
    CategoryDeviationStats,
    DecisionComparisonPayload,
    EntityDeviationStats,
    ExecutionMode,
    HoleCardOption,
    SimulationConfigRequest,
    Soft17Option,
    SurrenderOption,
    TableRulesConfig,
)
from app.engine.types import DealerStyle, Soft17Rule, SurrenderRule


def test_table_rules_config_defaults():
    """Verify that default casino rules match standard house rules."""
    config = TableRulesConfig()
    assert config.soft_17_rule == Soft17Option.STAND
    assert config.blackjack_payout == 1.5
    assert config.hole_card_rule == HoleCardOption.AMERICAN_PEEK
    assert config.insurance_allowed is True
    assert config.surrender_rule == SurrenderOption.LATE
    assert config.double_after_split is True
    assert config.max_split_hands == 4
    assert config.resplit_aces is False
    assert config.hit_split_aces is False
    assert config.num_decks == 6
    assert config.penetration == 0.75
    assert config.burn_cards_count == 0
    assert config.initial_bankroll == 1000.0
    assert config.min_bet == 10.0
    assert config.max_bet == 500.0
    assert config.stop_on_all_bankrupt is True

    # Check conversion to domain TableRules
    domain_rules = config.to_table_rules()
    assert domain_rules.soft_17_rule == Soft17Rule.STAND_ON_SOFT_17
    assert domain_rules.hole_card_rule == DealerStyle.AMERICAN_PEEK
    assert domain_rules.surrender_rule == SurrenderRule.LATE
    assert domain_rules.blackjack_payout_ratio == 1.5
    assert domain_rules.num_decks == 6
    assert domain_rules.penetration == 0.75
    assert domain_rules.min_bet == 10.0
    assert domain_rules.max_bet == 500.0


def test_table_rules_custom_conversion():
    """Verify conversion of custom rules permutations."""
    config = TableRulesConfig(
        soft_17_rule=Soft17Option.HIT,
        hole_card_rule=HoleCardOption.EUROPEAN_NO_HOLE_CARD,
        surrender_rule=SurrenderOption.EARLY,
        blackjack_payout=1.2,
        num_decks=2,
        penetration=0.65,
        burn_cards_count=2,
        min_bet=25.0,
        max_bet=1000.0,
        initial_bankroll=5000.0,
    )
    domain_rules = config.to_table_rules()
    assert domain_rules.soft_17_rule == Soft17Rule.HIT_SOFT_17
    assert domain_rules.hole_card_rule == DealerStyle.EUROPEAN_NO_HOLE_CARD
    assert domain_rules.surrender_rule == SurrenderRule.EARLY
    assert domain_rules.blackjack_payout_ratio == 1.2
    assert domain_rules.num_decks == 2
    assert domain_rules.penetration == 0.65
    assert domain_rules.burn_cards_count == 2


def test_table_rules_validation_errors():
    """Verify boundary and consistency constraints."""
    # min_bet > max_bet
    with pytest.raises(ValidationError, match="min_bet .* cannot exceed max_bet"):
        TableRulesConfig(min_bet=100.0, max_bet=50.0)

    # invalid num_decks
    with pytest.raises(ValidationError, match="num_decks must be one of"):
        TableRulesConfig(num_decks=3)

    # penetration out of bounds
    with pytest.raises(ValidationError):
        TableRulesConfig(penetration=0.90)

    with pytest.raises(ValidationError):
        TableRulesConfig(penetration=0.40)

    # burn_cards_count out of bounds
    with pytest.raises(ValidationError):
        TableRulesConfig(burn_cards_count=6)

    # initial_bankroll < min_bet
    with pytest.raises(ValidationError, match="initial_bankroll .* must be at least table min_bet"):
        TableRulesConfig(initial_bankroll=100.0, min_bet=150.0, max_bet=500.0)


def test_simulation_config_request_defaults():
    """Verify default parameters for SimulationConfigRequest."""
    req = SimulationConfigRequest()
    assert req.max_rounds == 10
    assert req.num_simulations == 1
    assert req.execution_mode == ExecutionMode.VISUALIZED
    assert req.delay_ms == 300.0
    assert req.seed is None
    assert req.entities == ["optimal", "jev", "laya"]
    assert req.mock_mode is False


def test_simulation_config_request_validation():
    """Verify entity validation in SimulationConfigRequest."""
    # Empty entities
    with pytest.raises(ValidationError, match="At least one entity must be specified"):
        SimulationConfigRequest(entities=[])

    # Unknown entity
    with pytest.raises(ValidationError, match="Invalid entity 'unknown'"):
        SimulationConfigRequest(entities=["jev", "unknown"])

    # Valid subset
    req = SimulationConfigRequest(entities=["jev", "optimal"], mock_mode=True)
    assert req.entities == ["jev", "optimal"]
    assert req.mock_mode is True


def test_entity_deviation_stats_tracking():
    """Verify running strategy deviation statistics accumulation."""
    stats = EntityDeviationStats(entity_id="jev")
    assert stats.total_decisions == 0
    assert stats.optimality_rate == 1.0

    # Optimal Hard Total decision
    comp1 = DecisionComparisonPayload(
        is_optimal=True,
        optimal_action="stand",
        actual_action="stand",
        category="hard_total",
        reasoning="Stand on Hard 17 vs 10",
    )
    stats.record_decision(comp1)
    assert stats.total_decisions == 1
    assert stats.optimal_decisions == 1
    assert stats.deviations_count == 0
    assert stats.optimality_rate == 1.0
    assert stats.categories["hard_total"].total_decisions == 1
    assert stats.categories["hard_total"].deviations == 0
    assert stats.categories["hard_total"].optimality_rate == 1.0

    # Suboptimal Pair Split decision
    comp2 = DecisionComparisonPayload(
        is_optimal=False,
        optimal_action="split",
        actual_action="hit",
        category="pair_split",
        reasoning="Always split 8s",
    )
    stats.record_decision(comp2)
    assert stats.total_decisions == 2
    assert stats.optimal_decisions == 1
    assert stats.deviations_count == 1
    assert stats.optimality_rate == 0.5
    assert stats.categories["pair_split"].total_decisions == 1
    assert stats.categories["pair_split"].deviations == 1
    assert stats.categories["pair_split"].optimality_rate == 0.0

    # Bet deviation tracking
    stats.record_bet(is_optimal=True, bet_delta=0.0)
    stats.record_bet(is_optimal=False, bet_delta=20.0)
    assert stats.betting_deviations.total_bets == 2
    assert stats.betting_deviations.suboptimal_bets == 1
    assert stats.betting_deviations.total_bet_delta == 20.0
    assert stats.betting_deviations.avg_bet_delta == 10.0
