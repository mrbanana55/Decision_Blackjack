"""Quickstart scenarios test suite (Task T021).

Validates all 5 scenarios from specs/004-database-persistence/quickstart.md:
1. Schema Auto-Provisioning & Entity Integrity
2. Real-Time Event Ingestion from Simulation Run
3. Historical Round Replay & Analytical Metrics
4. Structured Run Archival Export
5. Cascading Run Deletion
"""

import asyncio
import json
import tempfile
from decimal import Decimal

import pytest

try:
    from app.persistence.database import (
        check_db_health,
        close_db,
        get_engine,
        get_session_factory,
        init_db,
    )
    from app.persistence.exporter import RunExporter
    from app.persistence.listener import SimulationPersistenceListener
    from app.persistence.models import (
        Base,
        HoleCardRule,
        Soft17Rule,
        SplitAcesBlackjackRule,
        SurrenderRule,
    )
    from app.persistence.repositories import RunRepository
    from app.simulation import (
        BasicStrategyAgent,
        FakeJevAgent,
        FakeLayaAgent,
        SimulationConfig,
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
    from backend.app.persistence.exporter import RunExporter
    from backend.app.persistence.listener import SimulationPersistenceListener
    from backend.app.persistence.models import (
        Base,
        HoleCardRule,
        Soft17Rule,
        SplitAcesBlackjackRule,
        SurrenderRule,
    )
    from backend.app.persistence.repositories import RunRepository
    from backend.app.simulation import (
        BasicStrategyAgent,
        FakeJevAgent,
        FakeLayaAgent,
        SimulationConfig,
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


def test_quickstart_scenario_1_schema_auto_provisioning():
    """Scenario 1: Schema Auto-Provisioning & Entity Integrity."""
    if not DB_AVAILABLE:
        pytest.skip("PostgreSQL container is unreachable.")

    async def _run():
        engine = get_engine()
        assert await check_db_health(engine) is True
        await init_db(engine)
        assert len(Base.metadata.tables) == 15
        await close_db()

    asyncio.run(_run())


def test_quickstart_scenarios_2_through_5_lifecycle():
    """Scenarios 2-5: Event Ingestion -> Replay & Metrics -> Export -> Cascading Deletion."""
    if not DB_AVAILABLE:
        pytest.skip("PostgreSQL container is unreachable.")

    async def _run():
        session_factory = get_session_factory()
        await init_db()

        # Step 1: Create Run in DB (Scenario 2 setup)
        async with session_factory() as session:
            repo = RunRepository(session)
            run = await repo.create_run({
                "soft_17_rule": Soft17Rule.STAND,
                "blackjack_payout_ratio": Decimal("1.5"),
                "split_aces_blackjack_rule": SplitAcesBlackjackRule.NATURAL,
                "hole_card_rule": HoleCardRule.AMERICAN_PEEK,
                "surrender_rule": SurrenderRule.LATE,
                "number_of_decks": 6,
                "initial_bankroll": Decimal("1000.0"),
                "minimum_bet": Decimal("25.0"),
                "maximum_bet": Decimal("500.0"),
                "rounds_per_simulation": 2,
            })
            run_id = run.id

        # Step 2: Configure orchestrator and attach persistence listener (Scenario 2)
        config = SimulationConfig(
            session_id=str(run_id),
            max_rounds=2,
            seed=42,
            initial_bankroll=1000.0,
        )
        orchestrator = SimulationOrchestrator(config)
        orchestrator.add_entity("optimal", BasicStrategyAgent())
        orchestrator.add_entity("jev", FakeJevAgent(simulated_latency_ms=1.0))
        orchestrator.add_entity("laya", FakeLayaAgent(simulated_latency_ms=1.0))

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

        # Scenario 2 verification
        async with session_factory() as session:
            repo = RunRepository(session)
            run_record = await repo.get_run(run_id)
            assert run_record is not None
            assert len(run_record.simulations) > 0
            sim_id = run_record.simulations[0].id

            # Scenario 3: Historical Round Replay & Analytical Metrics
            summary = await repo.get_player_benchmark_summary(sim_id)
            assert len(summary) == 3
            for player_stat in summary:
                assert "player_type" in player_stat
                assert "agreement_pct" in player_stat
                assert player_stat["rounds_played"] == 2

            # Chronological round replay
            round_id = run_record.simulations[0].rounds[0].id
            replay = await repo.get_round_replay(round_id)
            assert replay is not None
            assert len(replay["cards"]) > 0
            assert len(replay["players"]) == 3

        # Scenario 4: Structured Run Archival Export
        with tempfile.TemporaryDirectory() as tmpdir:
            async with session_factory() as session:
                exporter = RunExporter(session, base_dir=tmpdir)
                export_file = await exporter.export_run_to_json(run_id)
                assert export_file.exists()
                with open(export_file, "r", encoding="utf-8") as f:  # noqa: ASYNC230
                    data = json.load(f)
                assert data["run_id"] == str(run_id)
                assert len(data["simulations"]) == 1

        # Scenario 5: Cascading Run Deletion
        async with session_factory() as session:
            repo = RunRepository(session)
            deleted = await repo.delete_run(run_id)
            assert deleted is True
            assert (await repo.get_run(run_id)) is None

        await close_db()

    asyncio.run(_run())
