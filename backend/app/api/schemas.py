"""Pydantic v2 schemas for simulation configuration, requests, responses, and events."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, model_validator

from app.engine.rules import TableRules
from app.engine.types import DealerStyle, Soft17Rule, SurrenderRule


class Soft17Option(str, Enum):
    """Soft 17 dealer action option."""
    STAND = "S17"
    HIT = "H17"


class HoleCardOption(str, Enum):
    """Dealer hole card style option."""
    AMERICAN_PEEK = "AMERICAN_PEEK"
    EUROPEAN_NO_HOLE_CARD = "EUROPEAN_NO_HOLE_CARD"


class SurrenderOption(str, Enum):
    """Player surrender rule option."""
    LATE = "LATE"
    EARLY = "EARLY"
    NO_SURRENDER = "NO_SURRENDER"


class ExecutionMode(str, Enum):
    """Simulation execution mode."""
    VISUALIZED = "visualized"
    FAST_BATCH = "fast_batch"


class TableRulesConfig(BaseModel):
    """Configurable table and casino rules matching house rules specification."""

    soft_17_rule: Soft17Option = Field(
        default=Soft17Option.STAND,
        description="Dealer stands on Soft 17 (S17) or hits (H17)",
    )
    blackjack_payout: float = Field(
        default=1.5,
        ge=1.0,
        le=2.0,
        description="Natural Blackjack payout multiplier: 1.5 (3:2), 1.2 (6:5), 1.0 (1:1)",
    )
    hole_card_rule: HoleCardOption = Field(
        default=HoleCardOption.AMERICAN_PEEK,
        description="American peek vs European No Hole Card (ENHC)",
    )
    insurance_allowed: bool = Field(
        default=True,
        description="Enable or disable 2:1 insurance side bet",
    )
    surrender_rule: SurrenderOption = Field(
        default=SurrenderOption.LATE,
        description="Surrender rule: LATE, EARLY, or NO_SURRENDER",
    )
    double_after_split: bool = Field(
        default=True,
        description="Permit doubling down on hands created by splitting (DAS)",
    )
    max_split_hands: int = Field(
        default=4,
        ge=1,
        le=4,
        description="Maximum simultaneous hands resulting from splits",
    )
    resplit_aces: bool = Field(
        default=False,
        description="Allow re-splitting pairs of Aces (RSA)",
    )
    hit_split_aces: bool = Field(
        default=False,
        description="Allow drawing more than one card to split Aces",
    )
    num_decks: int = Field(
        default=6,
        description="Number of 52-card decks in shoe: 1, 2, 4, 6, 8",
    )
    penetration: float = Field(
        default=0.75,
        ge=0.50,
        le=0.85,
        description="Shoe cut-card threshold percentage (50% to 85%)",
    )
    burn_cards_count: int = Field(
        default=0,
        ge=0,
        le=5,
        description="Number of cards discarded upon shoe initialization",
    )
    initial_bankroll: float = Field(
        default=1000.0,
        ge=100.0,
        le=1000000.0,
        description="Starting bankroll per player table",
    )
    min_bet: float = Field(
        default=10.0,
        ge=1.0,
        le=1000.0,
        description="Table minimum wager",
    )
    max_bet: float = Field(
        default=500.0,
        ge=10.0,
        le=50000.0,
        description="Table maximum wager",
    )
    stop_on_all_bankrupt: bool = Field(
        default=True,
        description="Halt simulation if all players are eliminated",
    )

    @model_validator(mode="after")
    def validate_rules_consistency(self) -> "TableRulesConfig":
        if self.min_bet > self.max_bet:
            raise ValueError(f"min_bet ({self.min_bet}) cannot exceed max_bet ({self.max_bet})")
        if self.num_decks not in (1, 2, 4, 6, 8):
            raise ValueError(f"num_decks must be one of [1, 2, 4, 6, 8], got {self.num_decks}")
        if self.initial_bankroll < self.min_bet:
            raise ValueError(
                f"initial_bankroll ({self.initial_bankroll}) must be at least table min_bet ({self.min_bet})"
            )
        return self

    def to_table_rules(self) -> TableRules:
        """Convert API rules config into domain TableRules instance."""
        soft_17 = (
            Soft17Rule.HIT_SOFT_17
            if self.soft_17_rule == Soft17Option.HIT
            else Soft17Rule.STAND_ON_SOFT_17
        )

        dealer_style = (
            DealerStyle.EUROPEAN_NO_HOLE_CARD
            if self.hole_card_rule == HoleCardOption.EUROPEAN_NO_HOLE_CARD
            else DealerStyle.AMERICAN_PEEK
        )

        if self.surrender_rule == SurrenderOption.EARLY:
            surrender = SurrenderRule.EARLY
        elif self.surrender_rule == SurrenderOption.NO_SURRENDER:
            surrender = SurrenderRule.NONE
        else:
            surrender = SurrenderRule.LATE

        return TableRules(
            soft_17_rule=soft_17,
            blackjack_payout_ratio=self.blackjack_payout,
            hole_card_rule=dealer_style,
            insurance_enabled=self.insurance_allowed,
            insurance_payout_ratio=2.0,
            surrender_rule=surrender,
            double_after_split=self.double_after_split,
            max_split_hands=self.max_split_hands,
            resplit_aces=self.resplit_aces,
            hit_split_aces=self.hit_split_aces,
            min_bet=self.min_bet,
            max_bet=self.max_bet,
            num_decks=self.num_decks,
            penetration=self.penetration,
            burn_cards_count=self.burn_cards_count,
        )


class SimulationConfigRequest(BaseModel):
    """Top-level request body for POST /api/simulations."""

    max_rounds: int = Field(
        default=10,
        ge=1,
        le=100000,
        description="Number of rounds to execute per simulation",
    )
    num_simulations: int = Field(
        default=1,
        ge=1,
        le=1000,
        description="Number of simulation runs to execute",
    )
    execution_mode: ExecutionMode = Field(
        default=ExecutionMode.VISUALIZED,
        description="visualized (streaming) or fast_batch (background)",
    )
    delay_ms: float = Field(
        default=300.0,
        ge=0.0,
        le=2000.0,
        description="Pacing delay in milliseconds between rounds for visualized mode",
    )
    seed: int | None = Field(
        default=None,
        description="Deterministic PRNG random seed (auto-generated if omitted)",
    )
    entities: list[str] = Field(
        default_factory=lambda: ["optimal", "jev", "laya"],
        description="Active decision providers: any subset of ['optimal', 'jev', 'laya']",
    )
    mock_mode: bool = Field(
        default=False,
        description="Use mock agents for offline testing without network services",
    )
    table_rules: TableRulesConfig = Field(
        default_factory=TableRulesConfig,
        description="House rules configuration",
    )

    @model_validator(mode="after")
    def validate_entities(self) -> "SimulationConfigRequest":
        allowed = {"optimal", "jev", "laya"}
        if not self.entities:
            raise ValueError("At least one entity must be specified in 'entities'")
        for entity in self.entities:
            if entity.lower() not in allowed:
                raise ValueError(
                    f"Invalid entity '{entity}'. Allowed entities are: {sorted(allowed)}"
                )
        return self


class SimulationResponse(BaseModel):
    """Simulation creation descriptor response."""

    session_id: str
    run_id: str
    status: str
    execution_mode: ExecutionMode
    current_round: int
    max_rounds: int
    num_simulations: int
    entities: list[str]
    websocket_url: str
    created_at: str
    table_rules: TableRulesConfig


class EntityMetricSummary(BaseModel):
    """Performance summary metrics for an entity in a run."""

    entity_id: str
    rounds_played: int
    net_profit: float
    current_bankroll: float
    win_rate: float
    optimality_rate: float


class SimulationListItem(BaseModel):
    """Summary record in historical simulations catalog."""

    run_id: str
    session_id: str
    status: str
    start_time: str
    end_time: str | None
    total_rounds: int
    max_rounds: int
    num_simulations: int
    seed: int
    entities: list[str]
    metrics: dict[str, EntityMetricSummary]


class SimulationListResponse(BaseModel):
    """Paginated collection of past simulation runs."""

    items: list[SimulationListItem]
    total: int
    page: int
    page_size: int


class ControlCommandRequest(BaseModel):
    """Payload for REST fallback POST /api/simulations/{session_id}/control."""

    command: str = Field(description="pause, resume, step, retry, stop, set_speed")
    level: str | None = Field(default=None, description="round or turn for step command")
    entity_id: str | None = Field(default=None, description="Entity to retry on PAUSED_ERROR")
    delay_ms: float | None = Field(default=None, ge=0.0, le=2000.0, description="New pacing delay")


class PurgeDatabaseResponse(BaseModel):
    """Response returned upon DELETE /api/database / POST /api/database/clear."""

    status: str = "cleared"
    tables_purged: int = 15
    cleared_tables: list[str]
    timestamp: str


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str


# ============================================================================
# Strategy Deviation Schemas
# ============================================================================

class DecisionComparisonPayload(BaseModel):
    """Evaluation record comparing an agent's turn action against Basic Strategy."""

    is_optimal: bool
    optimal_action: str
    actual_action: str
    category: str  # hard_total, soft_total, pair_split, surrender, insurance
    reasoning: str
    is_legal: bool = True


class CategoryDeviationStats(BaseModel):
    """Deviation statistics within a specific blackjack decision category."""

    total_decisions: int = 0
    deviations: int = 0
    optimality_rate: float = 1.0


class BetSpreadDeviationStats(BaseModel):
    """Deviation statistics comparing opening bets against the Hi-Lo bet spread."""

    total_bets: int = 0
    suboptimal_bets: int = 0
    total_bet_delta: float = 0.0
    avg_bet_delta: float = 0.0


class EntityDeviationStats(BaseModel):
    """Real-time aggregated comparative analytics for a player against Basic Strategy."""

    entity_id: str
    total_decisions: int = 0
    optimal_decisions: int = 0
    deviations_count: int = 0
    optimality_rate: float = 1.0
    categories: dict[str, CategoryDeviationStats] = Field(
        default_factory=lambda: {
            "hard_total": CategoryDeviationStats(),
            "soft_total": CategoryDeviationStats(),
            "pair_split": CategoryDeviationStats(),
            "surrender": CategoryDeviationStats(),
            "insurance": CategoryDeviationStats(),
        }
    )
    betting_deviations: BetSpreadDeviationStats = Field(
        default_factory=BetSpreadDeviationStats
    )

    def record_decision(self, comparison: DecisionComparisonPayload) -> None:
        """Update running deviation statistics with a new turn comparison."""
        self.total_decisions += 1
        if comparison.is_optimal:
            self.optimal_decisions += 1
        else:
            self.deviations_count += 1
        self.optimality_rate = (
            round(self.optimal_decisions / self.total_decisions, 4)
            if self.total_decisions > 0
            else 1.0
        )

        cat_key = comparison.category.lower()
        if cat_key not in self.categories:
            self.categories[cat_key] = CategoryDeviationStats()
        cat_stats = self.categories[cat_key]
        cat_stats.total_decisions += 1
        if not comparison.is_optimal:
            cat_stats.deviations += 1
        cat_stats.optimality_rate = (
            round((cat_stats.total_decisions - cat_stats.deviations) / cat_stats.total_decisions, 4)
            if cat_stats.total_decisions > 0
            else 1.0
        )

    def record_bet(self, is_optimal: bool, bet_delta: float) -> None:
        """Update running bet spread deviation statistics."""
        self.betting_deviations.total_bets += 1
        if not is_optimal:
            self.betting_deviations.suboptimal_bets += 1
        self.betting_deviations.total_bet_delta += abs(bet_delta)
        self.betting_deviations.avg_bet_delta = round(
            self.betting_deviations.total_bet_delta / self.betting_deviations.total_bets, 2
        )


class SimulationDeviationsResponse(BaseModel):
    """Response returned upon GET /api/simulations/{session_id}/deviations."""

    session_id: str
    current_round: int
    entities: dict[str, EntityDeviationStats]
    updated_at: str


class SimulationDetailResponse(BaseModel):
    """Detailed response for GET /api/simulations/{session_id}."""

    run_id: str
    session_id: str
    status: str
    start_time: str
    end_time: str | None
    total_rounds: int
    max_rounds: int
    num_simulations: int
    seed: int
    entities: list[str]
    table_rules: TableRulesConfig
    metrics: dict[str, EntityMetricSummary]
    deviations: dict[str, EntityDeviationStats]
