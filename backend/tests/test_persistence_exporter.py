"""Integration tests for RunExporter (User Story 3 - Run Archival & Export).

Verifies serialization of complete simulation runs into structured JSON artifacts
stored at /data/runs/[timestamp]/run_data.json.
"""

import asyncio
import json
import tempfile
import uuid
from datetime import UTC, datetime
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
    from app.persistence.models import (
        BankrollTransaction,
        Bet,
        BetType,
        CardEvent,
        CardEventType,
        CardRecipient,
        CharlieRule,
        Decision,
        DecisionType,
        Hand,
        HandResult,
        HandResultType,
        HandStatus,
        HoleCardRule,
        ModelProvider,
        ModelResponse,
        PlayerAction,
        PlayerRoundStatus,
        PlayerSession,
        PlayerType,
        Round,
        RoundPlayer,
        RoundStatus,
        Run,
        RunConfiguration,
        RunStatus,
        SessionStatus,
        Shoe,
        Simulation,
        SimulationStatus,
        Soft17Rule,
        SplitAcesBlackjackRule,
        SurrenderRule,
        TransactionType,
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
    from backend.app.persistence.models import (
        BankrollTransaction,
        Bet,
        BetType,
        CardEvent,
        CardEventType,
        CardRecipient,
        CharlieRule,
        Decision,
        DecisionType,
        Hand,
        HandResult,
        HandResultType,
        HandStatus,
        HoleCardRule,
        ModelProvider,
        ModelResponse,
        PlayerAction,
        PlayerRoundStatus,
        PlayerSession,
        PlayerType,
        Round,
        RoundPlayer,
        RoundStatus,
        Run,
        RunConfiguration,
        RunStatus,
        SessionStatus,
        Shoe,
        Simulation,
        SimulationStatus,
        Soft17Rule,
        SplitAcesBlackjackRule,
        SurrenderRule,
        TransactionType,
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


def test_exporter_serializes_complete_run_to_json():
    """Verify RunExporter writes complete run hierarchy to run_data.json."""
    if not DB_AVAILABLE:
        pytest.skip("PostgreSQL container is unreachable.")

    async def _run():
        session_factory = get_session_factory()
        await init_db()

        run_id = uuid.uuid4()
        now = datetime.now(UTC)

        # Build full populated Run hierarchy
        async with session_factory() as session:
            run = Run(
                id=run_id,
                status=RunStatus.COMPLETED,
                started_at=now,
                finished_at=now,
            )
            session.add(run)

            cfg = RunConfiguration(
                run_id=run.id,
                soft_17_rule=Soft17Rule.HIT,
                blackjack_payout_ratio=Decimal("1.500"),
                split_aces_blackjack_rule=SplitAcesBlackjackRule.COUNT_21,
                hole_card_rule=HoleCardRule.AMERICAN_PEEK,
                insurance_enabled=True,
                insurance_payout_ratio=Decimal("2.000"),
                surrender_rule=SurrenderRule.LATE,
                das_enabled=True,
                max_resplit=3,
                rsa_enabled=False,
                hit_split_aces=False,
                charlie_rule=CharlieRule.NONE,
                number_of_decks=6,
                penetration=Decimal("0.750"),
                burn_cards=1,
                initial_bankroll=Decimal("1000.00"),
                minimum_bet=Decimal("25.00"),
                maximum_bet=Decimal("500.00"),
                rounds_per_simulation=10,
                rounds_indefinite=False,
                simulations_count=1,
                simulations_indefinite=False,
                user_seed=42,
            )
            session.add(cfg)

            sim = Simulation(
                run_id=run.id,
                simulation_number=1,
                seed=42,
                status=SimulationStatus.COMPLETED,
                initial_bankroll=Decimal("1000.00"),
                final_bankroll=Decimal("1050.00"),
                started_at=now,
                finished_at=now,
            )
            session.add(sim)
            await session.flush()

            ps = PlayerSession(
                simulation_id=sim.id,
                player_type=PlayerType.OPTIMAL,
                initial_bankroll=Decimal("1000.00"),
                current_bankroll=Decimal("1050.00"),
                status=SessionStatus.ACTIVE,
            )
            session.add(ps)

            shoe = Shoe(
                simulation_id=sim.id,
                shoe_number=1,
                seed=42,
                card_order=["10S", "AH", "9D", "7C"],
                total_cards=312,
                penetration=Decimal("0.750"),
            )
            session.add(shoe)
            await session.flush()

            round_obj = Round(
                simulation_id=sim.id,
                round_number=1,
                status=RoundStatus.COMPLETED,
                dealer_final_value=20,
                started_at=now,
                finished_at=now,
            )
            session.add(round_obj)
            await session.flush()

            rp = RoundPlayer(
                round_id=round_obj.id,
                player_session_id=ps.id,
                bankroll_before=Decimal("1000.00"),
                bankroll_after=Decimal("1050.00"),
                status=PlayerRoundStatus.RESOLVED,
                started_at=now,
                finished_at=now,
            )
            session.add(rp)
            await session.flush()

            hand = Hand(
                round_player_id=rp.id,
                hand_number=1,
                is_initial=True,
                is_split=False,
                status=HandStatus.RESOLVED,
                final_value=21,
                is_blackjack=True,
            )
            session.add(hand)
            await session.flush()

            ce = CardEvent(
                round_id=round_obj.id,
                hand_id=hand.id,
                shoe_id=shoe.id,
                recipient=CardRecipient.HAND,
                event_type=CardEventType.DEAL,
                card="AH",
                sequence_number=1,
                shoe_position=0,
            )
            session.add(ce)

            dec = Decision(
                hand_id=hand.id,
                decision_number=1,
                decision_type=DecisionType.INITIAL,
                action=PlayerAction.STAND,
                confidence_pct=Decimal("100.00"),
                running_count=0,
                true_count=Decimal("0.00"),
                bankroll_at_decision=Decimal("975.00"),
                optimal_reference_action=PlayerAction.STAND,
                agrees_with_optimal=True,
                state_snapshot={"cards": ["10S", "AH"]},
            )
            session.add(dec)
            await session.flush()

            mr = ModelResponse(
                decision_id=dec.id,
                provider=ModelProvider.BASIC_STRATEGY,
                model_name="basic-oracle",
                request_payload={"total": 21},
                response_payload={"action": "STAND"},
                latency_ms=1,
                requested_at=now,
                responded_at=now,
            )
            session.add(mr)

            bet = Bet(
                round_player_id=rp.id,
                hand_id=hand.id,
                bet_type=BetType.INITIAL,
                amount=Decimal("25.00"),
            )
            session.add(bet)

            hr = HandResult(
                hand_id=hand.id,
                result=HandResultType.BLACKJACK,
                player_value=21,
                dealer_value=20,
                payout_amount=Decimal("62.50"),
                net_amount=Decimal("37.50"),
            )
            session.add(hr)

            tx = BankrollTransaction(
                round_player_id=rp.id,
                hand_id=hand.id,
                bet_id=bet.id,
                transaction_type=TransactionType.PAYOUT,
                amount=Decimal("50.00"),
                balance_before=Decimal("975.00"),
                balance_after=Decimal("1025.00"),
            )
            session.add(tx)
            await session.commit()

        # Run Exporter into a temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            async with session_factory() as session:
                exporter = RunExporter(session=session, base_dir=tmpdir)
                output_path = await exporter.export_run_to_json(run_id=run_id)

                assert output_path.exists()
                assert output_path.name == "run_data.json"

                with open(output_path, "r", encoding="utf-8") as f:  # noqa: ASYNC230
                    data = json.load(f)

                assert data["run_id"] == str(run_id)
                assert data["status"] == "COMPLETED"
                assert "configuration" in data
                assert data["configuration"]["soft_17_rule"] == "HIT"
                assert len(data["simulations"]) == 1
                assert len(data["simulations"][0]["player_sessions"]) == 1
                assert len(data["simulations"][0]["rounds"]) == 1

                round_data = data["simulations"][0]["rounds"][0]
                assert len(round_data["round_players"]) == 1
                rp_data = round_data["round_players"][0]
                assert len(rp_data["hands"]) == 1
                assert len(rp_data["hands"][0]["decisions"]) == 1
                assert rp_data["hands"][0]["decisions"][0]["action"] == "STAND"
                assert rp_data["hands"][0]["decisions"][0]["model_response"]["model_name"] == "basic-oracle"

            # Cleanup DB
            async with session_factory() as session:
                loaded_run = await session.get(Run, run_id)
                if loaded_run:
                    await session.delete(loaded_run)
                    await session.commit()

        await close_db()

    asyncio.run(_run())
