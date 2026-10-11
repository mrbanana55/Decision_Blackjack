"""Canonical enums and domain types for the Simulation Orchestrator."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import uuid
from app.engine.card import Card
from app.engine.rules import TableRules
from app.engine.types import Action


class SessionStatus(str, Enum):
    """Lifecycle status of an active simulation session."""

    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    PAUSED_ERROR = "paused_error"
    STOPPED = "stopped"
    COMPLETED = "completed"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.value.lower() == other.lower()
        return super().__eq__(other)

    def __hash__(self) -> int:
        return hash(self.value)


class EntityType(str, Enum):
    """Category of the decision entity participating in a simulation."""

    OPTIMAL = "optimal"
    JEV = "jev"
    LAYA = "laya"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.value.lower() == other.lower()
        return super().__eq__(other)

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(slots=True)
class SimulationConfig:
    """Configuration governing an automated simulation experiment."""

    session_id: str = field(default_factory=lambda: f"sim-{uuid.uuid4().hex[:8]}")
    seed: int = 42
    max_rounds: int = 100
    initial_bankroll: float = 1000.0
    table_rules: TableRules = field(default_factory=TableRules)
    stop_on_all_bankrupt: bool = True


@dataclass(slots=True)
class DecisionContext:
    """Observable table context supplied to a DecisionProvider."""

    session_id: str
    round_number: int
    hand_index: int
    player_cards: list[Card]
    player_total: int
    is_soft: bool
    dealer_upcard: Card | None
    legal_actions: list[Action]
    can_insure: bool = False
    true_count: float = 0.0


@dataclass(slots=True)
class AgentDecision:
    """Action decision produced by an agent with confidence and latency telemetry."""

    action: Action
    confidence: float = 1.0
    latency_ms: float = 0.0
    reasoning: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SimulationMetrics:
    """Cumulative performance metrics for an entity table in a session."""

    entity_id: str
    entity_type: EntityType
    rounds_played: int = 0
    starting_bankroll: float = 1000.0
    current_bankroll: float = 1000.0
    net_profit: float = 0.0
    wins: int = 0
    losses: int = 0
    pushes: int = 0
    blackjacks: int = 0
    is_eliminated: bool = False


@dataclass
class SimulationSession:
    """Runtime snapshot of an orchestrated simulation session."""

    session_id: str
    status: SessionStatus
    current_round: int
    max_rounds: int
    seed: int
    start_time: str
    end_time: str | None = None
    metrics: dict[str, SimulationMetrics] = field(default_factory=dict)
