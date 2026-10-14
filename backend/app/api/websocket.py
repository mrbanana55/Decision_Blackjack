"""Native FastAPI WebSocket endpoint for live simulation event streaming and flow control."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.manager import simulation_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/simulations/{session_id}")
async def websocket_simulation_endpoint(websocket: WebSocket, session_id: str) -> None:
    """Bidirectional WebSocket connection streaming live telemetry events and accepting flow control commands."""
    record = simulation_manager.get_session(session_id)
    if not record:
        # Close connection immediately with custom 4404 Session Not Found code
        await websocket.close(code=4404, reason="Session Not Found")
        return

    await websocket.accept()
    simulation_manager.add_websocket(session_id, websocket)

    try:
        # Send immediate initial SESSION_SNAPSHOT frame
        orch = record.orchestrator
        snapshot = {
            "event_type": "SESSION_SNAPSHOT",
            "session_id": session_id,
            "round_number": orch.current_round,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "status": orch.status.value.upper(),
                "execution_mode": record.execution_mode.value,
                "delay_ms": record.delay_ms,
                "max_rounds": record.config.max_rounds,
                "current_round": orch.current_round,
                "entities": record.config.entities,
                "tables": {
                    tid: {
                        "bankroll": tbl.current_bankroll,
                        "rounds_played": tbl.rounds_played,
                        "shoe_generation": tbl.shoe_generation + 1,
                        "cards_remaining": tbl.cards_remaining,
                        "running_count": tbl.running_count,
                        "true_count": tbl.true_count,
                    }
                    for tid, tbl in orch.tables.items()
                },
                "deviations": {
                    ent: stats.model_dump()
                    for ent, stats in record.deviations.items()
                },
            },
        }
        await websocket.send_json(snapshot)

        # If simulation is initializing and in visualized mode, start execution loop now that client is connected
        if orch.status.value.lower() == "initializing":
            simulation_manager.start_simulation(session_id)

        # Listen for client flow control and configuration commands
        while True:
            data = await websocket.receive_json()
            command = str(data.get("command", "")).lower()

            if command == "start":
                if orch.status.value.lower() == "initializing":
                    simulation_manager.start_simulation(session_id)
                else:
                    await simulation_manager.resume(session_id)
            elif command == "pause":
                await simulation_manager.pause(session_id)
            elif command == "resume":
                await simulation_manager.resume(session_id)
            elif command == "step":
                level = str(data.get("level", "round")).lower()
                await simulation_manager.step(session_id, level=level)
            elif command == "set_speed":
                delay_ms = float(data.get("delay_ms", 300.0))
                await simulation_manager.set_speed(session_id, delay_ms)
            elif command == "stop":
                await simulation_manager.stop(session_id)
            elif command == "retry":
                entity_id = data.get("entity_id")
                await simulation_manager.retry(session_id, entity_id=entity_id)
            else:
                logger.warning("Unrecognized client command received: '%s'", command)

    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected from session %s", session_id)
    except Exception as exc:
        logger.debug("WebSocket error for session %s: %s", session_id, exc)
    finally:
        simulation_manager.remove_websocket(session_id, websocket)
