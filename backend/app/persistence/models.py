"""SQLAlchemy 2.0 ORM models and PostgreSQL ENUMs for Decision_Blackjack.

Maps the complete 15-entity relational schema across 6 functional domains:
1. Execution:     Run, RunConfiguration, Simulation
2. Participants:  PlayerSession
3. Shoes:         Shoe, PlayerShoeState
4. Game Flow:     Round, RoundPlayer, Hand, CardEvent
5. Decisions/AI:  Decision, ModelResponse
6. Economy:       Bet, HandResult, BankrollTransaction
"""

import enum
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base class for all persistence models."""


# ============================================================================
# ENUM DEFINITIONS (Inherit from str for JSON/string serialization)
# ============================================================================

class RunStatus(str, enum.Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    PAUSE_REQUESTED = "PAUSE_REQUESTED"
    PAUSED = "PAUSED"
    ERROR = "ERROR"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class SimulationStatus(str, enum.Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    BANKRUPT = "BANKRUPT"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"


class PlayerType(str, enum.Enum):
    JEV = "JEV"
    LAYA = "LAYA"
    OPTIMAL = "OPTIMAL"


class SessionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    BANKRUPT = "BANKRUPT"
    ERROR = "ERROR"


class TerminationReason(str, enum.Enum):
    ROUNDS_COMPLETED = "ROUNDS_COMPLETED"
    ALL_BANKRUPT = "ALL_BANKRUPT"
    USER_STOPPED = "USER_STOPPED"
    ERROR = "ERROR"


class RoundStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class PlayerRoundStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"
    BUSTED = "BUSTED"
    SURRENDERED = "SURRENDERED"
    BLACKJACK = "BLACKJACK"


class HandStatus(str, enum.Enum):
    IN_PLAY = "IN_PLAY"
    RESOLVED = "RESOLVED"
    BUSTED = "BUSTED"
    DOUBLED = "DOUBLED"
    SURRENDERED = "SURRENDERED"


class CardRecipient(str, enum.Enum):
    DEALER = "DEALER"
    HAND = "HAND"


class CardEventType(str, enum.Enum):
    DEAL = "DEAL"
    BURN = "BURN"
    REVEAL = "REVEAL"


class DecisionType(str, enum.Enum):
    INITIAL = "INITIAL"
    AFTER_HIT = "AFTER_HIT"
    AFTER_SPLIT = "AFTER_SPLIT"
    INSURANCE = "INSURANCE"


class PlayerAction(str, enum.Enum):
    HIT = "HIT"
    STAND = "STAND"
    DOUBLE = "DOUBLE"
    SPLIT = "SPLIT"
    SURRENDER = "SURRENDER"
    INSURANCE_ACCEPT = "INSURANCE_ACCEPT"
    INSURANCE_DECLINE = "INSURANCE_DECLINE"


class ModelProvider(str, enum.Enum):
    SYSTEM_ONE = "SYSTEM_ONE"
    LOCAL_MODEL = "LOCAL_MODEL"
    BASIC_STRATEGY = "BASIC_STRATEGY"


class BetType(str, enum.Enum):
    INITIAL = "INITIAL"
    DOUBLE = "DOUBLE"
    SPLIT = "SPLIT"
    INSURANCE = "INSURANCE"


class HandResultType(str, enum.Enum):
    WIN = "WIN"
    LOSS = "LOSS"
    PUSH = "PUSH"
    BLACKJACK = "BLACKJACK"
    BUST = "BUST"
    SURRENDER = "SURRENDER"


class TransactionType(str, enum.Enum):
    BET = "BET"
    PAYOUT = "PAYOUT"
    REFUND = "REFUND"
    INSURANCE = "INSURANCE"
    SURRENDER = "SURRENDER"
    ADJUSTMENT = "ADJUSTMENT"


class Soft17Rule(str, enum.Enum):
    STAND = "STAND"
    HIT = "HIT"


class HoleCardRule(str, enum.Enum):
    AMERICAN_PEEK = "AMERICAN_PEEK"
    ENHC = "ENHC"


class SplitAcesBlackjackRule(str, enum.Enum):
    NATURAL = "NATURAL"
    COUNT_21 = "COUNT_21"


class SurrenderRule(str, enum.Enum):
    NONE = "NONE"
    LATE = "LATE"


class CharlieRule(str, enum.Enum):
    NONE = "NONE"
    FIVE_CARD = "FIVE_CARD"
    SIX_CARD = "SIX_CARD"
    SEVEN_CARD = "SEVEN_CARD"


def _utcnow() -> datetime:
    return datetime.now(UTC)


TIMESTAMPTZ = DateTime(timezone=True)


# ============================================================================
# 1. EXECUTION DOMAIN MODELS
# ============================================================================

class Run(Base):
    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[RunStatus] = mapped_column(
        ENUM(RunStatus, name="run_status", create_type=True),
        nullable=False,
        default=RunStatus.CREATED,
    )
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False, default=_utcnow)
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_directory: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    configuration: Mapped["RunConfiguration"] = relationship(
        "RunConfiguration",
        back_populates="run",
        uselist=False,
        cascade="all, delete-orphan",
    )
    simulations: Mapped[list["Simulation"]] = relationship(
        "Simulation",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="Simulation.simulation_number",
    )


class RunConfiguration(Base):
    __tablename__ = "run_configurations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Table Rules
    soft_17_rule: Mapped[Soft17Rule] = mapped_column(
        ENUM(Soft17Rule, name="soft_17_rule", create_type=True),
        nullable=False,
    )
    blackjack_payout_ratio: Mapped[Decimal] = mapped_column(Numeric(5, 3), nullable=False)
    split_aces_blackjack_rule: Mapped[SplitAcesBlackjackRule] = mapped_column(
        ENUM(SplitAcesBlackjackRule, name="split_aces_blackjack_rule", create_type=True),
        nullable=False,
    )
    hole_card_rule: Mapped[HoleCardRule] = mapped_column(
        ENUM(HoleCardRule, name="hole_card_rule", create_type=True),
        nullable=False,
    )
    insurance_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    insurance_payout_ratio: Mapped[Decimal] = mapped_column(Numeric(5, 3), nullable=False, default=Decimal("2.000"))
    surrender_rule: Mapped[SurrenderRule] = mapped_column(
        ENUM(SurrenderRule, name="surrender_rule", create_type=True),
        nullable=False,
    )
    das_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    max_resplit: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=3)
    rsa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    hit_split_aces: Mapped[bool] = mapped_column(Boolean, nullable=False)
    charlie_rule: Mapped[CharlieRule] = mapped_column(
        ENUM(CharlieRule, name="charlie_rule", create_type=True),
        nullable=False,
        default=CharlieRule.NONE,
    )
    number_of_decks: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=6)
    penetration: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    burn_cards: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    initial_bankroll: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    minimum_bet: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    maximum_bet: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Experiment Setup
    rounds_per_simulation: Mapped[int] = mapped_column(Integer, nullable=False)
    rounds_indefinite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    simulations_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    simulations_indefinite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    user_seed: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    optimal_bet_spread: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Relationship
    run: Mapped["Run"] = relationship("Run", back_populates="configuration")


class Simulation(Base):
    __tablename__ = "simulations"
    __table_args__ = (
        UniqueConstraint("run_id", "simulation_number", name="uq_simulation_run_number"),
        CheckConstraint("simulation_number > 0", name="chk_simulation_number_positive"),
        Index("idx_simulation_run_id", "run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    simulation_number: Mapped[int] = mapped_column(Integer, nullable=False)
    seed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[SimulationStatus] = mapped_column(
        ENUM(SimulationStatus, name="simulation_status", create_type=True),
        nullable=False,
        default=SimulationStatus.RUNNING,
    )
    initial_bankroll: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    final_bankroll: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    termination_reason: Mapped[TerminationReason | None] = mapped_column(
        ENUM(TerminationReason, name="termination_reason", create_type=True),
        nullable=True,
    )
    started_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False, default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)

    # Relationships
    run: Mapped["Run"] = relationship("Run", back_populates="simulations")
    player_sessions: Mapped[list["PlayerSession"]] = relationship(
        "PlayerSession",
        back_populates="simulation",
        cascade="all, delete-orphan",
    )
    shoes: Mapped[list["Shoe"]] = relationship(
        "Shoe",
        back_populates="simulation",
        cascade="all, delete-orphan",
        order_by="Shoe.shoe_number",
    )
    rounds: Mapped[list["Round"]] = relationship(
        "Round",
        back_populates="simulation",
        cascade="all, delete-orphan",
        order_by="Round.round_number",
    )


# ============================================================================
# 2. PARTICIPANTS DOMAIN MODELS
# ============================================================================

class PlayerSession(Base):
    __tablename__ = "player_sessions"
    __table_args__ = (
        UniqueConstraint("simulation_id", "player_type", name="uq_player_session_sim_type"),
        Index("idx_player_session_sim_type", "simulation_id", "player_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("simulations.id", ondelete="CASCADE"),
        nullable=False,
    )
    player_type: Mapped[PlayerType] = mapped_column(
        ENUM(PlayerType, name="player_type", create_type=True),
        nullable=False,
    )
    initial_bankroll: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    current_bankroll: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[SessionStatus] = mapped_column(
        ENUM(SessionStatus, name="session_status", create_type=True),
        nullable=False,
        default=SessionStatus.ACTIVE,
    )

    # Relationships
    simulation: Mapped["Simulation"] = relationship("Simulation", back_populates="player_sessions")
    shoe_states: Mapped[list["PlayerShoeState"]] = relationship(
        "PlayerShoeState",
        back_populates="player_session",
        cascade="all, delete-orphan",
    )
    round_players: Mapped[list["RoundPlayer"]] = relationship(
        "RoundPlayer",
        back_populates="player_session",
        cascade="all, delete-orphan",
    )


# ============================================================================
# 3. SHOES DOMAIN MODELS
# ============================================================================

class Shoe(Base):
    __tablename__ = "shoes"
    __table_args__ = (
        UniqueConstraint("simulation_id", "shoe_number", name="uq_shoe_sim_number"),
        Index("idx_shoe_sim_number", "simulation_id", "shoe_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("simulations.id", ondelete="CASCADE"),
        nullable=False,
    )
    shoe_number: Mapped[int] = mapped_column(Integer, nullable=False)
    seed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    card_order: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    total_cards: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    burn_cards: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    penetration: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    generated_by_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("player_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False, default=_utcnow)

    # Relationships
    simulation: Mapped["Simulation"] = relationship("Simulation", back_populates="shoes")
    player_states: Mapped[list["PlayerShoeState"]] = relationship(
        "PlayerShoeState",
        back_populates="shoe",
        cascade="all, delete-orphan",
    )
    card_events: Mapped[list["CardEvent"]] = relationship(
        "CardEvent",
        back_populates="shoe",
        cascade="all, delete-orphan",
    )


class PlayerShoeState(Base):
    __tablename__ = "player_shoe_states"
    __table_args__ = (
        UniqueConstraint("player_session_id", "shoe_id", name="uq_player_shoe_state_session_shoe"),
        CheckConstraint("current_position >= 0", name="chk_shoe_state_position_non_negative"),
        Index("idx_player_shoe_state_session_shoe", "player_session_id", "shoe_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("player_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    shoe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shoes.id", ondelete="CASCADE"),
        nullable=False,
    )
    current_position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cards_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    running_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    true_count: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=Decimal("0.00"))
    started_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False, default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)

    # Relationships
    player_session: Mapped["PlayerSession"] = relationship("PlayerSession", back_populates="shoe_states")
    shoe: Mapped["Shoe"] = relationship("Shoe", back_populates="player_states")


# ============================================================================
# 4. GAME FLOW DOMAIN MODELS
# ============================================================================

class Round(Base):
    __tablename__ = "rounds"
    __table_args__ = (
        UniqueConstraint("simulation_id", "round_number", name="uq_round_sim_number"),
        CheckConstraint("round_number > 0", name="chk_round_number_positive"),
        Index("idx_round_sim_number", "simulation_id", "round_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("simulations.id", ondelete="CASCADE"),
        nullable=False,
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[RoundStatus] = mapped_column(
        ENUM(RoundStatus, name="round_status", create_type=True),
        nullable=False,
        default=RoundStatus.IN_PROGRESS,
    )
    dealer_final_value: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    dealer_blackjack: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dealer_bust: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    started_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False, default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)

    # Relationships
    simulation: Mapped["Simulation"] = relationship("Simulation", back_populates="rounds")
    round_players: Mapped[list["RoundPlayer"]] = relationship(
        "RoundPlayer",
        back_populates="round",
        cascade="all, delete-orphan",
    )
    card_events: Mapped[list["CardEvent"]] = relationship(
        "CardEvent",
        back_populates="round",
        cascade="all, delete-orphan",
        order_by="CardEvent.sequence_number",
    )


class RoundPlayer(Base):
    __tablename__ = "round_players"
    __table_args__ = (
        UniqueConstraint("round_id", "player_session_id", name="uq_round_player_round_session"),
        Index("idx_round_player_round_session", "round_id", "player_session_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    round_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rounds.id", ondelete="CASCADE"),
        nullable=False,
    )
    player_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("player_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    bankroll_before: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    bankroll_after: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[PlayerRoundStatus] = mapped_column(
        ENUM(PlayerRoundStatus, name="player_round_status", create_type=True),
        nullable=False,
        default=PlayerRoundStatus.ACTIVE,
    )
    started_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False, default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)

    # Relationships
    round: Mapped["Round"] = relationship("Round", back_populates="round_players")
    player_session: Mapped["PlayerSession"] = relationship("PlayerSession", back_populates="round_players")
    hands: Mapped[list["Hand"]] = relationship(
        "Hand",
        back_populates="round_player",
        cascade="all, delete-orphan",
        order_by="Hand.hand_number",
    )
    bets: Mapped[list["Bet"]] = relationship(
        "Bet",
        back_populates="round_player",
        cascade="all, delete-orphan",
    )
    transactions: Mapped[list["BankrollTransaction"]] = relationship(
        "BankrollTransaction",
        back_populates="round_player",
        cascade="all, delete-orphan",
    )


class Hand(Base):
    __tablename__ = "hands"
    __table_args__ = (
        Index("idx_hand_round_player", "round_player_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    round_player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("round_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_hand_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hands.id", ondelete="CASCADE"),
        nullable=True,
    )
    hand_number: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    is_initial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_split: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[HandStatus] = mapped_column(
        ENUM(HandStatus, name="hand_status", create_type=True),
        nullable=False,
        default=HandStatus.IN_PLAY,
    )
    final_value: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    is_blackjack: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_bust: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    round_player: Mapped["RoundPlayer"] = relationship("RoundPlayer", back_populates="hands")
    parent_hand: Mapped["Hand | None"] = relationship(
        "Hand",
        remote_side=[id],
        back_populates="child_hands",
    )
    child_hands: Mapped[list["Hand"]] = relationship(
        "Hand",
        back_populates="parent_hand",
        cascade="all, delete-orphan",
    )
    card_events: Mapped[list["CardEvent"]] = relationship(
        "CardEvent",
        back_populates="hand",
        cascade="all, delete-orphan",
        order_by="CardEvent.sequence_number",
    )
    decisions: Mapped[list["Decision"]] = relationship(
        "Decision",
        back_populates="hand",
        cascade="all, delete-orphan",
        order_by="Decision.decision_number",
    )
    result: Mapped["HandResult | None"] = relationship(
        "HandResult",
        back_populates="hand",
        uselist=False,
        cascade="all, delete-orphan",
    )
    bets: Mapped[list["Bet"]] = relationship(
        "Bet",
        back_populates="hand",
        cascade="all, delete-orphan",
    )
    transactions: Mapped[list["BankrollTransaction"]] = relationship(
        "BankrollTransaction",
        back_populates="hand",
        cascade="all, delete-orphan",
    )


class CardEvent(Base):
    __tablename__ = "card_events"
    __table_args__ = (
        CheckConstraint("sequence_number > 0", name="chk_card_event_sequence_positive"),
        CheckConstraint("shoe_position >= 0", name="chk_card_event_position_non_negative"),
        Index("idx_card_event_round_seq", "round_id", "sequence_number"),
        Index("idx_card_event_shoe_pos", "shoe_id", "shoe_position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    round_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rounds.id", ondelete="CASCADE"),
        nullable=False,
    )
    hand_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hands.id", ondelete="CASCADE"),
        nullable=True,
    )
    shoe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shoes.id", ondelete="CASCADE"),
        nullable=False,
    )
    recipient: Mapped[CardRecipient] = mapped_column(
        ENUM(CardRecipient, name="card_recipient", create_type=True),
        nullable=False,
    )
    event_type: Mapped[CardEventType] = mapped_column(
        ENUM(CardEventType, name="card_event_type", create_type=True),
        nullable=False,
        default=CardEventType.DEAL,
    )
    card: Mapped[str] = mapped_column(String(4), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    shoe_position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False, default=_utcnow)

    # Relationships
    round: Mapped["Round"] = relationship("Round", back_populates="card_events")
    hand: Mapped["Hand | None"] = relationship("Hand", back_populates="card_events")
    shoe: Mapped["Shoe"] = relationship("Shoe", back_populates="card_events")


# ============================================================================
# 5. DECISIONS & AI DOMAIN MODELS
# ============================================================================

class Decision(Base):
    __tablename__ = "decisions"
    __table_args__ = (
        CheckConstraint("decision_number > 0", name="chk_decision_number_positive"),
        CheckConstraint("confidence_pct >= 0.0 AND confidence_pct <= 100.0", name="chk_decision_confidence_range"),
        Index("idx_decision_hand_num", "hand_id", "decision_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hands.id", ondelete="CASCADE"),
        nullable=False,
    )
    decision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    decision_type: Mapped[DecisionType] = mapped_column(
        ENUM(DecisionType, name="decision_type", create_type=True),
        nullable=False,
    )
    action: Mapped[PlayerAction] = mapped_column(
        ENUM(PlayerAction, name="player_action", create_type=True),
        nullable=False,
    )
    confidence_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    running_count: Mapped[int] = mapped_column(Integer, nullable=False)
    true_count: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    bankroll_at_decision: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    optimal_reference_action: Mapped[PlayerAction] = mapped_column(
        ENUM(PlayerAction, name="player_action", create_type=False),
        nullable=False,
    )
    agrees_with_optimal: Mapped[bool] = mapped_column(Boolean, nullable=False)
    state_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False, default=_utcnow)

    # Relationships
    hand: Mapped["Hand"] = relationship("Hand", back_populates="decisions")
    model_response: Mapped["ModelResponse | None"] = relationship(
        "ModelResponse",
        back_populates="decision",
        uselist=False,
        cascade="all, delete-orphan",
    )


class ModelResponse(Base):
    __tablename__ = "model_responses"
    __table_args__ = (
        Index("idx_model_response_decision", "decision_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("decisions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    provider: Mapped[ModelProvider] = mapped_column(
        ENUM(ModelProvider, name="model_provider", create_type=True),
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    response_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    http_status: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)
    responded_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)

    # Relationship
    decision: Mapped["Decision"] = relationship("Decision", back_populates="model_response")


# ============================================================================
# 6. ECONOMY DOMAIN MODELS
# ============================================================================

class Bet(Base):
    __tablename__ = "bets"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="chk_bet_amount_non_negative"),
        Index("idx_bet_round_player", "round_player_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    round_player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("round_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    hand_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hands.id", ondelete="CASCADE"),
        nullable=True,
    )
    bet_type: Mapped[BetType] = mapped_column(
        ENUM(BetType, name="bet_type", create_type=True),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False, default=_utcnow)

    # Relationships
    round_player: Mapped["RoundPlayer"] = relationship("RoundPlayer", back_populates="bets")
    hand: Mapped["Hand | None"] = relationship("Hand", back_populates="bets")
    transactions: Mapped[list["BankrollTransaction"]] = relationship(
        "BankrollTransaction",
        back_populates="bet",
        cascade="all, delete-orphan",
    )


class HandResult(Base):
    __tablename__ = "hand_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hands.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    result: Mapped[HandResultType] = mapped_column(
        ENUM(HandResultType, name="hand_result_type", create_type=True),
        nullable=False,
    )
    player_value: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    dealer_value: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    payout_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False, default=_utcnow)

    # Relationship
    hand: Mapped["Hand"] = relationship("Hand", back_populates="result")


class BankrollTransaction(Base):
    __tablename__ = "bankroll_transactions"
    __table_args__ = (
        Index("idx_bankroll_tx_round_player_created", "round_player_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    round_player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("round_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    hand_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hands.id", ondelete="CASCADE"),
        nullable=True,
    )
    bet_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bets.id", ondelete="CASCADE"),
        nullable=True,
    )
    transaction_type: Mapped[TransactionType] = mapped_column(
        ENUM(TransactionType, name="transaction_type", create_type=True),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    balance_before: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False, default=_utcnow)

    # Relationships
    round_player: Mapped["RoundPlayer"] = relationship("RoundPlayer", back_populates="transactions")
    hand: Mapped["Hand | None"] = relationship("Hand", back_populates="transactions")
    bet: Mapped["Bet | None"] = relationship("Bet", back_populates="transactions")
