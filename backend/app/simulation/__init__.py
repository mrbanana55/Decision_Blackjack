from app.simulation.events import (
    EventEmitter,
    EventListener,
    EventType,
    SimulationEvent,
)
from app.simulation.interfaces import (
    AgentFaultError,
    DecisionProvider,
    EventPublisher,
    IllegalAgentActionError,
    OrchestratorController,
    SimulationError,
    SimulationStateError,
)
from app.simulation.orchestrator import SimulationOrchestrator
from app.simulation.shoe_pool import ShoePool
from app.simulation.table import EntityTable
from app.simulation.types import (
    AgentDecision,
    DecisionContext,
    EntityType,
    SessionStatus,
    SimulationConfig,
    SimulationMetrics,
    SimulationSession,
)

__all__ = [
    "AgentDecision",
    "AgentFaultError",
    "BasicStrategyAgent",
    "DecisionContext",
    "DecisionProvider",
    "EntityTable",
    "EntityType",
    "EventEmitter",
    "EventListener",
    "EventPublisher",
    "EventType",
    "FakeJevAgent",
    "FakeLayaAgent",
    "IllegalAgentActionError",
    "JevAgent",
    "LayaAgent",
    "OrchestratorController",
    "SessionStatus",
    "ShoePool",
    "SimulationConfig",
    "SimulationError",
    "SimulationEvent",
    "SimulationMetrics",
    "SimulationOrchestrator",
    "SimulationSession",
    "SimulationStateError",
]


def __getattr__(name: str):
    if name == "JevAgent":
        from app.integrations.jev import JevAgent
        return JevAgent
    if name == "LayaAgent":
        from app.integrations.laya import LayaAgent
        return LayaAgent
    if name in ("BasicStrategyAgent", "FakeJevAgent", "FakeLayaAgent"):
        import app.simulation.agents as agents_mod
        return getattr(agents_mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
