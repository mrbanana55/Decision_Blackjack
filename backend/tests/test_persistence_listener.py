"""Integration tests for SimulationPersistenceListener.

Verifies real-time event ingestion, entity translation, optimal reference action capture,
AI model response auditing, atomic batch flushing, and orchestrator integration.
"""

import asyncio
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

try:
    from app.persistence.database import (
        check_db_health,
        close_db,
        get_engine,
        get_session_factory,
        init_db,
    )
    from app.persistence.listener import SimulationPersistenceListener
    from app.persistence.models import (
        Decision,
        Hand,
        ModelProvider,
        PlayerAction,
        Round,
        RoundPlayer,
        Run,
        RunStatus,
        Simulation,
        SimulationStatus,
        TerminationReason,
    )
    from app.simulation import (
        BasicStrategyAgent,
        EventEmitter,
        EventType,
        FakeJevAgent,
        FakeLayaAgent,
        SimulationConfig,
        SimulationEvent,
        SimulationOrchestrator,
    )
except ImportError:
    from backend.app.persistence.database import (
        check_db_health,
        close_db,
        get_engine,
        get_session_factory,
        init_db,
    )
    from backend.app.persistence.listener import SimulationPersistenceListener
    from backend.app.persistence.models import (
        Decision,
        Hand,
        ModelProvider,
        PlayerAction,
        Round,
        RoundPlayer,
        Run,
        RunStatus,
        Simulation,
        SimulationStatus,
        TerminationReason,
    )
    from backend.app.simulation import (
        BasicStrategyAgent,
        EventEmitter,
        EventType,
        FakeJevAgent,
        FakeLayaAgent,
        SimulationConfig,
        SimulationEvent,
        SimulationOrchestrator,
    )


def is_db_available() -> bool:
    try:
        engine = get_engine()
        loop = asyncio.new_event_loop()
        healthy = loop.run_until_complete(check_db_health(engine))
        loop.run_until_complete(close_db())
        loop.close()
        return healthy
    except Exception:  # noqa: BLE001
        return False


DB_AVAILABLE = is_db_available()


def test_listener_attach_detach():
    """Verify listener attaches to and detaches from EventEmitter."""
    bus = EventEmitter()
    run_id = uuid.uuid4()
    listener = SimulationPersistenceListener(run_id=run_id, event_emitter=bus)

    assert bus._listeners.get(None) is None or listener.handle_event not in bus._listeners.get(None, [])
    listener.attach()
    assert listener.handle_event in bus._listeners.get(None, [])
    listener.detach()
    assert listener.handle_event not in bus._listeners.get(None, [])


def test_listener_synthetic_event_ingestion():
    """Verify end-to-end ingestion of synthetic events into PostgreSQL."""
    if not DB_AVAILABLE:
        pytest.skip("PostgreSQL container is unreachable.")

    async def _run():
        try:
            session_factory = get_session_factory()
            await init_db()

            run_id = uuid.uuid4()
            bus = EventEmitter()

            # Pre-create Run record
            async with session_factory() as session:
                run = Run(id=run_id, status=RunStatus.RUNNING)
                session.add(run)
                await session.commit()

            listener = SimulationPersistenceListener(
                run_id=run_id,
                event_emitter=bus,
                batch_rounds=1,
                session_factory=session_factory,
            )
            listener.attach()

            # 1. SESSION_STARTED
            await bus.emit(
                SimulationEvent(
                    session_id=str(run_id),
                    event_type=EventType.SESSION_STARTED,
                    payload={
                        "session_id": str(run_id),
                        "seed": 42,
                        "max_rounds": 1,
                        "initial_bankroll": 1000.0,
                        "entities": ["optimal", "jev"],
                    },
                )
            )

            # 2. ROUND_STARTED
            await bus.emit(
                SimulationEvent(
                    session_id=str(run_id),
                    event_type=EventType.ROUND_STARTED,
                    payload={"round_number": 1, "active_entities": ["optimal", "jev"]},
                )
            )

            # 3. CARD_DEALT
            await bus.emit(
                SimulationEvent(
                    session_id=str(run_id),
                    event_type=EventType.CARD_DEALT,
                    payload={
                        "entity_id": "jev",
                        "round_number": 1,
                        "player_cards": ["10S", "6H"],
                        "dealer_upcard": "9D",
                    },
                )
            )

            # 4. DECISION_APPLIED with optimal comparison and AI telemetry
            await bus.emit(
                SimulationEvent(
                    session_id=str(run_id),
                    event_type=EventType.DECISION_APPLIED,
                    payload={
                        "entity_id": "jev",
                        "round_number": 1,
                        "action": "hit",
                        "confidence": 0.85,
                        "latency_ms": 120.0,
                        "reasoning": "Hard 16 against 9 calls for hit.",
                        "comparison": {
                            "is_optimal": True,
                            "optimal_action": "hit",
                            "category": "HARD_TOTAL",
                        },
                        "model_provider": "SYSTEM_ONE",
                        "model_name": "jev-system-one",
                        "request_payload": {"prompt": "16 vs 9"},
                        "response_payload": {"action": "hit"},
                    },
                )
            )

            # 5. ROUND_SETTLED
            await bus.emit(
                SimulationEvent(
                    session_id=str(run_id),
                    event_type=EventType.ROUND_SETTLED,
                    payload={
                        "entity_id": "jev",
                        "round_number": 1,
                        "net_profit": 25.0,
                        "final_bankroll": 1025.0,
                        "outcomes": [{"outcome": "win", "net_profit": 25.0}],
                    },
                )
            )
            await bus.emit(
                SimulationEvent(
                    session_id=str(run_id),
                    event_type=EventType.ROUND_SETTLED,
                    payload={
                        "entity_id": "optimal",
                        "round_number": 1,
                        "net_profit": -25.0,
                        "final_bankroll": 975.0,
                        "outcomes": [{"outcome": "loss", "net_profit": -25.0}],
                    },
                )
            )

            # 6. SESSION_COMPLETED
            await bus.emit(
                SimulationEvent(
                    session_id=str(run_id),
                    event_type=EventType.SESSION_COMPLETED,
                    payload={"total_rounds": 1},
                )
            )

            await listener.flush()
            listener.detach()

            # Query database and verify all entities were persisted
            async with session_factory() as session:
                # Check Simulation and PlayerSessions
                stmt = (
                    select(Simulation)
                    .options(selectinload(Simulation.player_sessions))
                    .where(Simulation.run_id == run_id)
                )
                res = await session.execute(stmt)
                sim = res.scalar_one_or_none()
                assert sim is not None
                assert sim.status == SimulationStatus.COMPLETED
                assert len(sim.player_sessions) >= 2

                # Check Round, RoundPlayer, Hands, Decisions
                stmt_round = (
                    select(Round)
                    .options(
                        selectinload(Round.round_players)
                        .selectinload(RoundPlayer.hands)
                        .selectinload(Hand.decisions)
                        .selectinload(Decision.model_response),
                        selectinload(Round.card_events),
                    )
                    .where(Round.simulation_id == sim.id)
                )
                res_round = await session.execute(stmt_round)
                round_obj = res_round.scalar_one_or_none()
                assert round_obj is not None
                assert round_obj.round_number == 1
                assert len(round_obj.round_players) == 2
                assert len(round_obj.card_events) >= 3

                # Check Decision and ModelResponse for Jev
                all_decisions = [
                    d
                    for rp in round_obj.round_players
                    for h in rp.hands
                    for d in h.decisions
                ]
                assert len(all_decisions) >= 1
                jev_dec = all_decisions[0]
                assert jev_dec.action == PlayerAction.HIT
                assert jev_dec.optimal_reference_action == PlayerAction.HIT
                assert jev_dec.agrees_with_optimal is True
                assert jev_dec.model_response is not None
                assert jev_dec.model_response.provider == ModelProvider.SYSTEM_ONE
                assert jev_dec.model_response.latency_ms == 120

                # Cleanup
                loaded_run = await session.get(Run, run_id)
                if loaded_run:
                    await session.delete(loaded_run)
                    await session.commit()
        finally:
            await close_db()

    asyncio.run(_run())


def test_listener_with_simulation_orchestrator():
    """Verify live integration of listener with running SimulationOrchestrator."""
    if not DB_AVAILABLE:
        pytest.skip("PostgreSQL container is unreachable.")

    async def _run():
        try:
            session_factory = get_session_factory()
            await init_db()

            run_id = uuid.uuid4()
            async with session_factory() as session:
                run = Run(id=run_id, status=RunStatus.CREATED)
                session.add(run)
                await session.commit()

            config = SimulationConfig(
                session_id=str(run_id),
                seed=42,
                max_rounds=2,
                initial_bankroll=1000.0,
            )
            orchestrator = SimulationOrchestrator(config)
            orchestrator.add_entity("optimal", BasicStrategyAgent())
            orchestrator.add_entity("jev", FakeJevAgent(simulated_latency_ms=2.0))
            orchestrator.add_entity("laya", FakeLayaAgent(simulated_latency_ms=2.0))

            listener = SimulationPersistenceListener(
                run_id=run_id,
                event_emitter=orchestrator.event_bus,
                batch_rounds=1,
                session_factory=session_factory,
            )
            listener.attach()

            await orchestrator.start()
            await listener.flush()
            listener.detach()

            # Verify rounds and participant sessions were stored
            async with session_factory() as session:
                stmt = (
                    select(Simulation)
                    .options(
                        selectinload(Simulation.player_sessions),
                        selectinload(Simulation.rounds),
                    )
                    .where(Simulation.run_id == run_id)
                )
                res = await session.execute(stmt)
                sim = res.scalar_one_or_none()
                assert sim is not None
                assert len(sim.player_sessions) == 3
                assert len(sim.rounds) == 2

                # Cleanup
                loaded_run = await session.get(Run, run_id)
                if loaded_run:
                    await session.delete(loaded_run)
                    await session.commit()
        finally:
            await close_db()

    asyncio.run(_run())


def test_listener_error_recovery():
    """Verify listener records ERROR status on orchestrator fault."""
    if not DB_AVAILABLE:
        pytest.skip("PostgreSQL container is unreachable.")

    async def _run():
        try:
            session_factory = get_session_factory()
            await init_db()

            run_id = uuid.uuid4()
            async with session_factory() as session:
                run = Run(id=run_id, status=RunStatus.RUNNING)
                session.add(run)
                await session.commit()

            bus = EventEmitter()
            listener = SimulationPersistenceListener(
                run_id=run_id,
                event_emitter=bus,
                batch_rounds=1,
                session_factory=session_factory,
            )
            listener.attach()

            await bus.emit(
                SimulationEvent(
                    session_id=str(run_id),
                    event_type=EventType.SESSION_STARTED,
                    payload={"session_id": str(run_id), "seed": 99},
                )
            )
            await bus.emit(
                SimulationEvent(
                    session_id=str(run_id),
                    event_type=EventType.SESSION_ERROR,
                    payload={"error": "LLM API Rate Limit Exceeded", "error_type": "RateLimitError"},
                )
            )

            await listener.flush()
            listener.detach()

            async with session_factory() as session:
                loaded_run = await session.get(Run, run_id)
                assert loaded_run is not None
                assert loaded_run.status == RunStatus.ERROR
                assert "Rate Limit" in (loaded_run.error_message or "")

                await session.delete(loaded_run)
                await session.commit()
        finally:
            await close_db()

    asyncio.run(_run())


def test_listener_session_stopped():
    """Verify listener records CANCELLED status and USER_STOPPED termination reason when session is stopped."""
    if not DB_AVAILABLE:
        pytest.skip("PostgreSQL container is unreachable.")

    async def _run():
        try:
            session_factory = get_session_factory()
            await init_db()

            run_id = uuid.uuid4()
            async with session_factory() as session:
                run = Run(id=run_id, status=RunStatus.RUNNING)
                session.add(run)
                await session.commit()

            bus = EventEmitter()
            listener = SimulationPersistenceListener(
                run_id=run_id,
                event_emitter=bus,
                batch_rounds=1,
                session_factory=session_factory,
            )
            listener.attach()

            await bus.emit(
                SimulationEvent(
                    session_id=str(run_id),
                    event_type=EventType.SESSION_STARTED,
                    payload={"session_id": str(run_id), "seed": 42},
                )
            )
            await bus.emit(
                SimulationEvent(
                    session_id=str(run_id),
                    event_type=EventType.SESSION_STOPPED,
                    payload={"session_id": str(run_id), "reason": "user_cancelled"},
                )
            )

            await listener.flush()
            listener.detach()

            async with session_factory() as session:
                loaded_run = await session.get(Run, run_id)
                assert loaded_run is not None
                assert loaded_run.status == RunStatus.CANCELLED

                stmt = select(Simulation).where(Simulation.run_id == run_id)
                res = await session.execute(stmt)
                sim = res.scalar_one_or_none()
                assert sim is not None
                assert sim.status == SimulationStatus.CANCELLED
                assert sim.termination_reason == TerminationReason.USER_STOPPED

                await session.delete(loaded_run)
                await session.commit()
        finally:
            await close_db()

    asyncio.run(_run())

