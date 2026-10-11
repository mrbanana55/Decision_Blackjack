"""Temporary mock agents simulating remote JEV API and local LAYA model inference.

These fake agents provide realistic latencies, confidence metrics, and configurable
fault simulation for development and testing. They will be swapped for real implementations
in future specs without changing the orchestrator core.
"""

import asyncio
import random
import time
from typing import Any
from app.engine.types import Action
from app.simulation.agents.basic_strategy import BasicStrategyAgent
from app.simulation.interfaces import AgentFaultError
from app.simulation.types import AgentDecision, DecisionContext, EntityType


class FakeJevAgent:
    """Mock agent simulating remote TypeSafe / Jev API inference."""

    def __init__(
        self,
        name: str = "FakeJev",
        simulated_latency_ms: float = 25.0,
        error_rate: float = 0.0,
        illegal_action_rate: float = 0.0,
        confidence: float = 0.88,
        fail_on_round: int | None = None,
    ) -> None:
        self._name = name
        self.simulated_latency_ms = simulated_latency_ms
        self.error_rate = error_rate
        self.illegal_action_rate = illegal_action_rate
        self.confidence = confidence
        self.fail_on_round = fail_on_round
        self._delegate = BasicStrategyAgent()
        self.fault_next: bool = False
        self.illegal_action_next: bool = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def entity_type(self) -> EntityType:
        return EntityType.JEV

    def inject_fault(self) -> None:
        """Trigger an intentional AgentFaultError on the next decision request."""
        self.fault_next = True

    def clear_fault(self) -> None:
        """Clear any primed fault injection."""
        self.fault_next = False
        self.fail_on_round = None

    def inject_illegal_action(self) -> None:
        """Trigger an intentional illegal action on the next decision request."""
        self.illegal_action_next = True

    async def get_decision(self, context: DecisionContext) -> AgentDecision:
        t0 = time.perf_counter()

        # Simulated network latency
        if self.simulated_latency_ms > 0:
            await asyncio.sleep(self.simulated_latency_ms / 1000.0)

        # Fault injection check
        is_round_fault = self.fail_on_round is not None and context.round_number == self.fail_on_round
        if self.fault_next or is_round_fault or (self.error_rate > 0 and random.random() < self.error_rate):
            self.fault_next = False
            raise AgentFaultError(f"Simulated JEV API network error for {self.name}")

        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        # Illegal action injection check
        if self.illegal_action_next or (self.illegal_action_rate > 0 and random.random() < self.illegal_action_rate):
            self.illegal_action_next = False
            # Find an action NOT in legal_actions
            for act in (Action.SURRENDER, Action.SPLIT, Action.DOUBLE):
                if act not in context.legal_actions:
                    return AgentDecision(
                        action=act,
                        confidence=0.5,
                        latency_ms=elapsed_ms,
                        reasoning="Intentionally illegal action for fault testing",
                        metadata={"injected_fault": True},
                    )

        # Base decision on basic strategy for plausible play
        base_decision = await self._delegate.get_decision(context)

        return AgentDecision(
            action=base_decision.action,
            confidence=self.confidence,
            latency_ms=elapsed_ms,
            reasoning=f"Jev System One reasoning: {base_decision.reasoning}",
            metadata={
                "model": "jev-system-one-mock",
                "tokens": 42,
                "simulated": True,
            },
        )


class FakeLayaAgent:
    """Mock agent simulating local deep learning / neural network inference."""

    def __init__(
        self,
        name: str = "FakeLaya",
        simulated_latency_ms: float = 10.0,
        error_rate: float = 0.0,
        illegal_action_rate: float = 0.0,
        confidence: float = 0.94,
    ) -> None:
        self._name = name
        self.simulated_latency_ms = simulated_latency_ms
        self.error_rate = error_rate
        self.illegal_action_rate = illegal_action_rate
        self.confidence = confidence
        self._delegate = BasicStrategyAgent()
        self.fault_next: bool = False
        self.illegal_action_next: bool = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def entity_type(self) -> EntityType:
        return EntityType.LAYA

    def inject_fault(self) -> None:
        """Trigger an intentional AgentFaultError on the next decision request."""
        self.fault_next = True

    def inject_illegal_action(self) -> None:
        """Trigger an intentional illegal action on the next decision request."""
        self.illegal_action_next = True

    async def get_decision(self, context: DecisionContext) -> AgentDecision:
        t0 = time.perf_counter()

        # Simulated local inference latency
        if self.simulated_latency_ms > 0:
            await asyncio.sleep(self.simulated_latency_ms / 1000.0)

        # Fault injection check
        if self.fault_next or (self.error_rate > 0 and random.random() < self.error_rate):
            self.fault_next = False
            raise AgentFaultError(f"Simulated LAYA inference tensor runtime exception for {self.name}")

        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        # Illegal action injection check
        if self.illegal_action_next or (self.illegal_action_rate > 0 and random.random() < self.illegal_action_rate):
            self.illegal_action_next = False
            for act in (Action.SURRENDER, Action.SPLIT, Action.DOUBLE):
                if act not in context.legal_actions:
                    return AgentDecision(
                        action=act,
                        confidence=0.5,
                        latency_ms=elapsed_ms,
                        reasoning="Intentionally illegal action for fault testing",
                        metadata={"injected_fault": True},
                    )

        base_decision = await self._delegate.get_decision(context)

        return AgentDecision(
            action=base_decision.action,
            confidence=self.confidence,
            latency_ms=elapsed_ms,
            reasoning=f"Laya neural network policy: {base_decision.reasoning}",
            metadata={
                "model": "laya-blackjack-policy-v1",
                "device": "cpu",
                "simulated": True,
            },
        )
