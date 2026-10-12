"""Core simulation orchestrator managing multi-table blackjack simulations."""

import asyncio
from datetime import datetime, timezone
from typing import Any
from app.engine.types import RoundPhase
from app.simulation.events import EventEmitter, EventType, SimulationEvent
from app.simulation.interfaces import (
    AgentFaultError,
    DecisionProvider,
    IllegalAgentActionError,
    OrchestratorController,
    SimulationError,
    SimulationStateError,
)
from app.simulation.shoe_pool import ShoePool
from app.simulation.table import EntityTable
from app.simulation.types import (
    AgentDecision,
    EntityType,
    SessionStatus,
    SimulationConfig,
    SimulationSession,
)


class SimulationOrchestrator(OrchestratorController):
    """Coordinates isolated blackjack tables, flow control, events, and fault handling."""

    def __init__(
        self,
        config: SimulationConfig,
        event_bus: EventEmitter | None = None,
    ) -> None:
        self.config: SimulationConfig = config
        self.event_bus: EventEmitter = event_bus if event_bus is not None else EventEmitter()
        self.shoe_pool: ShoePool = ShoePool(
            base_seed=config.seed,
            num_decks=config.table_rules.num_decks,
            penetration=getattr(config.table_rules, "penetration", 0.75),
        )
        self.tables: dict[str, EntityTable] = {}
        self._status: SessionStatus = SessionStatus.INITIALIZING
        self._current_round: int = 0
        self._start_time: str = datetime.now(timezone.utc).isoformat()
        self._end_time: str | None = None

        # Flow control primitives
        self._pause_event: asyncio.Event = asyncio.Event()
        self._pause_event.set()
        self._stop_requested: bool = False
        self._single_round_step: bool = False
        self._single_turn_step: bool = False
        self._step_target_round: int | None = None
        self._is_loop_running: bool = False

        # Fault tracking
        self.failed_entity_id: str | None = None
        self.last_error: Exception | None = None

    @property
    def status(self) -> SessionStatus:
        return self._status

    @property
    def current_round(self) -> int:
        return self._current_round

    @property
    def session(self) -> SimulationSession:
        return SimulationSession(
            session_id=self.config.session_id,
            status=self._status,
            current_round=self._current_round,
            max_rounds=self.config.max_rounds,
            seed=self.config.seed,
            start_time=self._start_time,
            end_time=self._end_time,
            metrics={tid: t.metrics for tid, t in self.tables.items()},
        )

    def add_entity(
        self,
        entity_id_or_provider: str | DecisionProvider,
        provider: DecisionProvider | None = None,
        initial_bankroll: float | None = None,
    ) -> EntityTable:
        """Register a decision entity and instantiate an isolated table with initial conditions.
        
        Supports both:
          orchestrator.add_entity("optimal", BasicStrategyAgent())
          orchestrator.add_entity(BasicStrategyAgent())
        """
        if self._status != SessionStatus.INITIALIZING:
            raise SimulationStateError(
                f"Cannot add entity in state '{self._status.value}'. Must be INITIALIZING."
            )

        if isinstance(entity_id_or_provider, str):
            entity_id = entity_id_or_provider
            if provider is None:
                raise ValueError("provider must be provided when entity_id is a string.")
            active_provider = provider
        else:
            active_provider = entity_id_or_provider
            eid = active_provider.name.lower()
            if eid.startswith("fake"):
                eid = eid[4:]
            if eid.endswith("agent"):
                eid = eid[:-5]
            entity_id = eid if eid else active_provider.entity_type.value

        if entity_id in self.tables:
            raise ValueError(f"Entity '{entity_id}' is already registered in this simulation.")

        bankroll = initial_bankroll if initial_bankroll is not None else self.config.initial_bankroll
        # Generation 0 shoe clone guarantees identical initial conditions across tables (FR-003)
        shoe = self.shoe_pool.get_shoe_for_generation(0)

        table = EntityTable(
            entity_id=entity_id,
            provider=active_provider,
            rules=self.config.table_rules,
            shoe=shoe,
            initial_bankroll=bankroll,
            shoe_generation=0,
        )
        self.tables[entity_id] = table
        return table

    async def _emit(self, event_type: EventType, payload: dict[str, Any]) -> None:
        """Helper to emit an event on the event bus."""
        event = SimulationEvent(
            session_id=self.config.session_id,
            event_type=event_type,
            payload=payload,
        )
        await self.event_bus.emit(event)

    def _should_stop(self) -> bool:
        """Evaluate composite stopping criteria (FR-012)."""
        if self._stop_requested:
            return True
        if self._current_round >= self.config.max_rounds:
            # Only stop if tables are not mid-round
            active = [t for t in self.tables.values() if not t.is_eliminated]
            if not active or all(t.phase in (RoundPhase.AWAITING_BET, RoundPhase.ROUND_COMPLETE) for t in active):
                return True
        if self.config.stop_on_all_bankrupt and self.tables:
            if all(t.is_eliminated for t in self.tables.values()):
                return True
        return False

    async def _check_and_handle_reshuffle(self, table: EntityTable) -> None:
        """Handle generational shoe reshuffling when cut-card threshold is crossed (FR-011)."""
        if table.reshuffle_needed:
            next_generation = table.shoe_generation + 1
            new_shoe = self.shoe_pool.get_shoe_for_generation(next_generation)
            table.adopt_shoe(new_shoe, next_generation)

            await self._emit(
                EventType.SHOE_RESHUFFLED,
                {
                    "entity_id": table.entity_id,
                    "round_number": self._current_round,
                    "generation": next_generation,
                },
            )

    async def _run_table_turn(self, table: EntityTable) -> None:
        """Execute turns on a single table until round settles or pause/error occurs."""
        while table.phase not in (RoundPhase.ROUND_COMPLETE, RoundPhase.AWAITING_BET):
            if self._stop_requested or self._status in (SessionStatus.PAUSED_ERROR, SessionStatus.PAUSED):
                return

            if table.phase == RoundPhase.INSURANCE_OFFERED:
                table.round_engine.submit_insurance(accept=False)

            elif table.phase == RoundPhase.PLAYER_TURNS:
                await self._emit(
                    EventType.TURN_REQUESTED,
                    {
                        "entity_id": table.entity_id,
                        "round_number": self._current_round,
                        "hand_index": table.round_engine.active_hand_index,
                        "legal_actions": [a.value for a in table.round_engine.get_legal_actions()],
                    },
                )

                decision = await table.play_turn(
                    session_id=self.config.session_id,
                    round_number=self._current_round,
                )

                if decision is not None:
                    payload = {
                        "entity_id": table.entity_id,
                        "round_number": self._current_round,
                        "action": decision.action.value,
                        "confidence": decision.confidence,
                        "latency_ms": decision.latency_ms,
                        "reasoning": decision.reasoning,
                    }
                    if decision.metadata:
                        payload["metadata"] = decision.metadata
                        if "model" in decision.metadata:
                            payload["model_name"] = decision.metadata["model"]
                        if "provider" in decision.metadata:
                            payload["model_provider"] = decision.metadata["provider"]
                        if "response_payload" in decision.metadata:
                            payload["response_payload"] = decision.metadata["response_payload"]
                    if "comparison" in decision.metadata:
                        payload["comparison"] = decision.metadata["comparison"]

                    await self._emit(EventType.DECISION_APPLIED, payload)

                if self._single_turn_step:
                    self._single_turn_step = False
                    self._status = SessionStatus.PAUSED
                    self._pause_event.clear()
                    await self._emit(EventType.SESSION_PAUSED, {"round": self._current_round})
                    return

            elif table.phase == RoundPhase.DEALER_TURN:
                table.round_engine.play_dealer_to_end()

            elif table.phase == RoundPhase.SETTLEMENT:
                settlement = table.settle_round()
                await self._emit(
                    EventType.ROUND_SETTLED,
                    {
                        "entity_id": table.entity_id,
                        "round_number": self._current_round,
                        "net_profit": settlement.net_profit,
                        "final_bankroll": settlement.final_bankroll,
                        "outcomes": [
                            {"outcome": ho.outcome.value, "net_profit": ho.net_profit}
                            for ho in settlement.hand_outcomes
                        ],
                    },
                )
                if table.is_eliminated:
                    await self._emit(
                        EventType.ENTITY_ELIMINATED,
                        {
                            "entity_id": table.entity_id,
                            "round_number": self._current_round,
                            "final_bankroll": table.current_bankroll,
                        },
                    )
                return

    async def _execute_round_barrier(self) -> None:
        """Advance all active tables through one round concurrently with a round barrier (FR-004, FR-005)."""
        active_tables = [t for t in self.tables.values() if not t.is_eliminated]
        if not active_tables:
            return

        # Check if active tables need a new round started
        need_deal = any(t.phase in (RoundPhase.AWAITING_BET, RoundPhase.ROUND_COMPLETE) for t in active_tables)
        if need_deal:
            self._current_round += 1
            round_num = self._current_round

            # Reshuffle check prior to start of round
            for table in active_tables:
                await self._check_and_handle_reshuffle(table)

            await self._emit(
                EventType.ROUND_STARTED,
                {
                    "round_number": round_num,
                    "active_entities": [t.entity_id for t in active_tables],
                },
            )

            # Start round for all active tables
            min_bet = self.config.table_rules.min_bet
            for table in active_tables:
                if hasattr(table, "start_round_async"):
                    await table.start_round_async(round_number=round_num)
                else:
                    table.start_round()
                await self._emit(
                    EventType.CARD_DEALT,
                    {
                        "entity_id": table.entity_id,
                        "round_number": round_num,
                        "player_cards": [str(c) for c in table.round_engine.player_hands[0].cards],
                        "dealer_upcard": str(table.round_engine.dealer_hand.upcard),
                    },
                )

        # Run active tables concurrently with round barrier
        # If any table raises an exception, fail fast! (FR-009)
        tasks = [
            asyncio.create_task(self._run_table_turn(table))
            for table in active_tables
        ]

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, res in enumerate(results):
                if isinstance(res, Exception):
                    failing_table = active_tables[i]
                    self.failed_entity_id = failing_table.entity_id
                    self.last_error = res
                    self._status = SessionStatus.PAUSED_ERROR
                    self._pause_event.clear()

                    await self._emit(
                        EventType.SESSION_ERROR,
                        {
                            "entity_id": failing_table.entity_id,
                            "round_number": self._current_round,
                            "error": str(res),
                            "error_type": type(res).__name__,
                        },
                    )
                    return
        except Exception as e:
            self.last_error = e
            self._status = SessionStatus.PAUSED_ERROR
            self._pause_event.clear()
            return

    async def _simulation_loop(self) -> None:
        """Main simulation execution loop."""
        self._is_loop_running = True
        try:
            while not self._should_stop():
                await self._pause_event.wait()
                if self._stop_requested or self._status in (SessionStatus.PAUSED_ERROR, SessionStatus.STOPPED):
                    break

                if self._status == SessionStatus.PAUSED:
                    break

                await self._execute_round_barrier()

                if self._status in (SessionStatus.PAUSED_ERROR, SessionStatus.PAUSED, SessionStatus.STOPPED):
                    break

                if self._single_round_step:
                    active = [t for t in self.tables.values() if not t.is_eliminated]
                    all_complete = not active or all(t.phase in (RoundPhase.ROUND_COMPLETE, RoundPhase.AWAITING_BET) for t in active)
                    if self._current_round >= (self._step_target_round or 0) and all_complete:
                        self._single_round_step = False
                        self._step_target_round = None
                        self._status = SessionStatus.PAUSED
                        self._pause_event.clear()
                        await self._emit(EventType.SESSION_PAUSED, {"round": self._current_round})
                        break

            # Handle terminal conditions
            if self._stop_requested:
                self._status = SessionStatus.STOPPED
                self._end_time = datetime.now(timezone.utc).isoformat()
                await self._emit(EventType.SESSION_STOPPED, {"round": self._current_round})
            elif (
                self._status not in (SessionStatus.PAUSED_ERROR, SessionStatus.PAUSED, SessionStatus.STOPPED)
                and self._should_stop()
            ):
                self._status = SessionStatus.COMPLETED
                self._end_time = datetime.now(timezone.utc).isoformat()
                await self._emit(
                    EventType.SESSION_COMPLETED,
                    {
                        "total_rounds": self._current_round,
                        "metrics": {tid: t.metrics.__dict__ for tid, t in self.tables.items()},
                    },
                )
        finally:
            self._is_loop_running = False

    async def start(self) -> None:
        """Launch the simulation session and execute configured rounds."""
        if self._status not in (SessionStatus.INITIALIZING, SessionStatus.PAUSED):
            raise SimulationStateError(
                f"Cannot start simulation from status '{self._status.value}'."
            )

        if not self.tables:
            raise SimulationError("Cannot start simulation with no registered entity tables.")

        self._status = SessionStatus.RUNNING
        self._pause_event.set()
        await self._emit(
            EventType.SESSION_STARTED,
            {
                "session_id": self.config.session_id,
                "seed": self.config.seed,
                "max_rounds": self.config.max_rounds,
                "entities": list(self.tables.keys()),
            },
        )

        await self._simulation_loop()

    async def pause(self) -> None:
        """Suspend execution cleanly at the current turn/round boundary."""
        if self._status not in (SessionStatus.RUNNING, SessionStatus.PAUSED):
            return

        self._pause_event.clear()
        self._status = SessionStatus.PAUSED
        await self._emit(EventType.SESSION_PAUSED, {"round": self._current_round})

    async def resume(self) -> None:
        """Resume execution from a paused or paused-error state."""
        if self._status not in (SessionStatus.PAUSED, SessionStatus.PAUSED_ERROR):
            raise SimulationStateError(
                f"Cannot resume simulation from status '{self._status.value}'."
            )

        self._status = SessionStatus.RUNNING
        self._pause_event.set()
        await self._emit(EventType.SESSION_RESUMED, {"round": self._current_round})

        if not self._is_loop_running:
            await self._simulation_loop()

    async def step_round(self) -> None:
        """Advance all active tables by exactly one complete round, then pause."""
        if self._status not in (SessionStatus.INITIALIZING, SessionStatus.PAUSED):
            raise SimulationStateError(
                f"Cannot step round from status '{self._status.value}'."
            )

        self._step_target_round = self._current_round + 1
        self._single_round_step = True
        self._status = SessionStatus.RUNNING
        self._pause_event.set()

        if self._is_loop_running:
            # Wait for background loop to complete the stepped round and pause
            while self._single_round_step and self._status == SessionStatus.RUNNING:
                await asyncio.sleep(0.001)
        else:
            await self._simulation_loop()

    async def step_turn(self) -> None:
        """Advance active tables by a single decision turn, then pause."""
        if self._status not in (SessionStatus.INITIALIZING, SessionStatus.PAUSED):
            raise SimulationStateError(
                f"Cannot step turn from status '{self._status.value}'."
            )

        self._single_turn_step = True
        self._status = SessionStatus.RUNNING
        self._pause_event.set()

        if self._is_loop_running:
            while self._single_turn_step and self._status == SessionStatus.RUNNING:
                await asyncio.sleep(0.001)
        else:
            await self._simulation_loop()

    async def retry_failed_entity(self, entity_id: str) -> None:
        """Retry a failed agent turn request after a transient fault and resume."""
        if self._status != SessionStatus.PAUSED_ERROR:
            raise SimulationStateError(
                f"Cannot retry entity from status '{self._status.value}'. Must be in PAUSED_ERROR."
            )
        if entity_id != self.failed_entity_id:
            raise ValueError(
                f"Entity '{entity_id}' is not the failed entity ('{self.failed_entity_id}')."
            )

        table = self.tables.get(entity_id)
        if not table:
            raise ValueError(f"Entity table '{entity_id}' not found.")

        # Clear error state and resume
        self.failed_entity_id = None
        self.last_error = None
        self._status = SessionStatus.RUNNING
        self._pause_event.set()

        await self._emit(
            EventType.SESSION_RESUMED,
            {"resumed_after_error": True, "entity_id": entity_id},
        )

        await self._run_table_turn(table)
        if not self._is_loop_running:
            await self._simulation_loop()

    async def stop(self) -> None:
        """Cancel ongoing execution, finalize metrics, and transition to STOPPED."""
        self._stop_requested = True
        self._pause_event.set()
        self._status = SessionStatus.STOPPED
        self._end_time = datetime.now(timezone.utc).isoformat()
        await self._emit(EventType.SESSION_STOPPED, {"round": self._current_round})
