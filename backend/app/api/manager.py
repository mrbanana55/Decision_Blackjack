"""In-memory simulation session manager and event bridge for WebSocket clients."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any
import uuid
from fastapi import WebSocket

from app.api.schemas import (
    DecisionComparisonPayload,
    EntityDeviationStats,
    ExecutionMode,
    SimulationConfigRequest,
)
from app.simulation.events import EventType, SimulationEvent
from app.simulation.orchestrator import SimulationOrchestrator
from app.simulation.types import SessionStatus

logger = logging.getLogger(__name__)


class ActiveSessionRecord:
    """In-memory runtime tracking container for an orchestrated simulation."""

    def __init__(
        self,
        session_id: str,
        run_id: str,
        config: SimulationConfigRequest,
        orchestrator: SimulationOrchestrator,
        delay_ms: float = 300.0,
        execution_mode: ExecutionMode = ExecutionMode.VISUALIZED,
    ) -> None:
        self.session_id: str = session_id
        self.run_id: str = run_id
        self.config: SimulationConfigRequest = config
        self.orchestrator: SimulationOrchestrator = orchestrator
        self.delay_ms: float = delay_ms
        self.execution_mode: ExecutionMode = execution_mode
        self.created_at: str = datetime.now(timezone.utc).isoformat()
        self.task: asyncio.Task[Any] | None = None
        self.websockets: set[WebSocket] = set()
        self.deviations: dict[str, EntityDeviationStats] = {
            entity: EntityDeviationStats(entity_id=entity)
            for entity in config.entities
        }
        self.lock: asyncio.Lock = asyncio.Lock()


class SimulationManager:
    """Coordinates active simulation sessions, background tasks, and WebSocket streaming."""

    def __init__(self) -> None:
        self._sessions: dict[str, ActiveSessionRecord] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    def register_session(
        self,
        session_id: str,
        run_id: str,
        config: SimulationConfigRequest,
        orchestrator: SimulationOrchestrator,
    ) -> ActiveSessionRecord:
        """Register a provisioned simulation orchestrator instance."""
        record = ActiveSessionRecord(
            session_id=session_id,
            run_id=run_id,
            config=config,
            orchestrator=orchestrator,
            delay_ms=config.delay_ms,
            execution_mode=config.execution_mode,
        )
        self._sessions[session_id] = record

        # Subscribe our event bridge to the orchestrator event bus
        orchestrator.event_bus.subscribe(None, lambda evt: self._handle_orchestrator_event(record, evt))
        return record

    def get_session(self, session_id: str) -> ActiveSessionRecord | None:
        """Lookup an active or initialized session by session_id."""
        return self._sessions.get(session_id)

    def list_sessions(self) -> list[ActiveSessionRecord]:
        """Return all registered in-memory simulation records."""
        return list(self._sessions.values())

    def has_active_simulations(self) -> bool:
        """Check if any simulation is currently RUNNING or PAUSED."""
        for record in self._sessions.values():
            if record.orchestrator.status in (
                SessionStatus.RUNNING,
                SessionStatus.PAUSED,
                SessionStatus.PAUSED_ERROR,
            ):
                return True
        return False

    def clear_completed_sessions(self) -> None:
        """Clear memory for sessions that are COMPLETED or STOPPED."""
        to_remove = [
            sid
            for sid, rec in self._sessions.items()
            if rec.orchestrator.status in (SessionStatus.COMPLETED, SessionStatus.STOPPED)
        ]
        for sid in to_remove:
            self._sessions.pop(sid, None)

    def add_websocket(self, session_id: str, websocket: WebSocket) -> None:
        """Register an open client WebSocket connection to a session."""
        record = self.get_session(session_id)
        if record:
            record.websockets.add(websocket)

    def remove_websocket(self, session_id: str, websocket: WebSocket) -> None:
        """Remove a disconnected client WebSocket."""
        record = self.get_session(session_id)
        if record and websocket in record.websockets:
            record.websockets.remove(websocket)

    async def broadcast(
        self,
        record: ActiveSessionRecord,
        event_type: str,
        round_number: int,
        payload: dict[str, Any],
    ) -> None:
        """Broadcast an event frame to all connected WebSocket clients for this session."""
        if not record.websockets:
            return

        frame = {
            "event_type": event_type,
            "session_id": record.session_id,
            "round_number": round_number,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }

        dead_sockets: set[WebSocket] = set()
        for ws in list(record.websockets):
            try:
                await ws.send_json(frame)
            except Exception:
                dead_sockets.add(ws)

        for dead in dead_sockets:
            record.websockets.discard(dead)

    async def _handle_orchestrator_event(
        self,
        record: ActiveSessionRecord,
        event: SimulationEvent,
    ) -> None:
        """Bridge orchestrator domain events to WebSocket frames and update real-time deviation metrics."""
        event_type_str = event.event_type.value.upper()
        round_number = record.orchestrator.current_round
        payload = dict(event.payload)

        # 1. Enrich DECISION_APPLIED -> DECISION_MADE with comparison data
        if event.event_type == EventType.DECISION_APPLIED:
            event_type_str = "DECISION_MADE"
            entity_id = payload.get("entity_id", "")
            action = payload.get("action", "")
            comparison_dict = payload.get("comparison")

            if comparison_dict:
                comp_payload = DecisionComparisonPayload(
                    is_optimal=comparison_dict.get("is_optimal", True),
                    optimal_action=comparison_dict.get("optimal_action", action),
                    actual_action=action,
                    category=comparison_dict.get("category", "hard_total"),
                    reasoning=comparison_dict.get("reasoning", ""),
                    is_legal=comparison_dict.get("is_legal", True),
                )
            else:
                comp_payload = DecisionComparisonPayload(
                    is_optimal=True,
                    optimal_action=action,
                    actual_action=action,
                    category="hard_total",
                    reasoning="Basic Strategy agreement",
                    is_legal=True,
                )

            # Record deviation in running stats
            if entity_id in record.deviations:
                record.deviations[entity_id].record_decision(comp_payload)

            payload["comparison"] = comp_payload.model_dump()
            payload["is_optimal"] = comp_payload.is_optimal
            payload["optimal_action"] = comp_payload.optimal_action

        # 2. Enrich ROUND_SETTLED with live running deviations snapshot
        elif event.event_type == EventType.ROUND_SETTLED:
            event_type_str = "ROUND_SETTLED"
            payload["running_deviations"] = {
                ent: stats.model_dump() for ent, stats in record.deviations.items()
            }

        # 3. Handle SESSION_COMPLETED
        elif event.event_type == EventType.SESSION_COMPLETED:
            event_type_str = "SESSION_COMPLETED"
            payload["final_deviations"] = {
                ent: stats.model_dump() for ent, stats in record.deviations.items()
            }

        # 4. Handle SESSION_ERROR
        elif event.event_type == EventType.SESSION_ERROR:
            event_type_str = "SESSION_ERROR"
            payload["allowed_actions"] = ["retry", "abort"]

        await self.broadcast(record, event_type_str, round_number, payload)

        # 5. Pacing delay enforcement for visualized mode at round settlement
        if (
            event.event_type == EventType.ROUND_SETTLED
            and record.execution_mode == ExecutionMode.VISUALIZED
            and record.delay_ms > 0
        ):
            await asyncio.sleep(record.delay_ms / 1000.0)

    def start_simulation(self, session_id: str) -> asyncio.Task[Any] | None:
        """Launch background async task to run the simulation loop."""
        record = self.get_session(session_id)
        if not record:
            raise ValueError(f"Simulation session '{session_id}' not found.")

        if record.orchestrator.status not in (SessionStatus.INITIALIZING, SessionStatus.PAUSED):
            return record.task

        async def _run() -> None:
            try:
                await record.orchestrator.start()
            except Exception as e:
                logger.exception("Simulation execution failed: %s", e)

        task = asyncio.create_task(_run())
        record.task = task
        return task

    async def pause(self, session_id: str) -> None:
        """Pause execution at next turn/round boundary."""
        record = self.get_session(session_id)
        if not record:
            raise ValueError(f"Session '{session_id}' not found.")
        await record.orchestrator.pause()

    async def resume(self, session_id: str) -> None:
        """Resume execution from paused state."""
        record = self.get_session(session_id)
        if not record:
            raise ValueError(f"Session '{session_id}' not found.")
        await record.orchestrator.resume()

    async def step(self, session_id: str, level: str = "round") -> None:
        """Step execution by single round or turn."""
        record = self.get_session(session_id)
        if not record:
            raise ValueError(f"Session '{session_id}' not found.")
        if level == "turn":
            await record.orchestrator.step_turn()
        else:
            await record.orchestrator.step_round()

    async def set_speed(self, session_id: str, delay_ms: float) -> None:
        """Dynamically adjust round pacing delay."""
        record = self.get_session(session_id)
        if not record:
            raise ValueError(f"Session '{session_id}' not found.")
        record.delay_ms = max(0.0, min(2000.0, float(delay_ms)))
        await self.broadcast(
            record,
            "SPEED_UPDATED",
            record.orchestrator.current_round,
            {"delay_ms": record.delay_ms},
        )

    async def stop(self, session_id: str) -> None:
        """Halt simulation execution."""
        record = self.get_session(session_id)
        if not record:
            raise ValueError(f"Session '{session_id}' not found.")
        await record.orchestrator.stop()

    async def retry(self, session_id: str, entity_id: str | None = None) -> None:
        """Retry a failed entity turn under RNF-02 fault recovery."""
        record = self.get_session(session_id)
        if not record:
            raise ValueError(f"Session '{session_id}' not found.")
        target_entity = entity_id or record.orchestrator.failed_entity_id
        if not target_entity:
            raise ValueError("No failed entity recorded to retry.")
        await record.orchestrator.retry_failed_entity(target_entity)


# Global singleton instance
simulation_manager = SimulationManager()
