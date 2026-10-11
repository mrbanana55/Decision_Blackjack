"""Query and analytical replay tests for RunRepository (User Story 4).

Verifies run creation, listing, chronological round replay timeline retrieval,
dynamic player benchmark calculations, and hard cascading deletion.
"""

import asyncio
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
        PlayerAction,
        PlayerRoundStatus,
        PlayerSession,
        PlayerType,
        Round,
        RoundPlayer,
        RoundStatus,
        Run,
        RunStatus,
        Shoe,
        Simulation,
        Soft17Rule,
        SplitAcesBlackjackRule,
        SurrenderRule,
        TransactionType,
    )
    from app.persistence.repositories import RunRepository
except ImportError:
    from backend.app.persistence.database import (
        check_db_health,
        close_db,
        get_engine,
        get_session_factory,
        init_db,
    )
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
        PlayerAction,
        PlayerRoundStatus,
        PlayerSession,
        PlayerType,
        Round,
        RoundPlayer,
        RoundStatus,
        Run,
        RunStatus,
        Shoe,
        Simulation,
        Soft17Rule,
        SplitAcesBlackjackRule,
        SurrenderRule,
        TransactionType,
    )
    from backend.app.persistence.repositories import RunRepository


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


def test_repository_run_crud():
    """Verify create_run, get_run, list_runs, and delete_run with cascade."""
    if not DB_AVAILABLE:
        pytest.skip("PostgreSQL container is unreachable.")

    async def _run():
        session_factory = get_session_factory()
        await init_db()

        async with session_factory() as session:
            repo = RunRepository(session)

            config_data = {
                "soft_17_rule": Soft17Rule.STAND,
                "blackjack_payout_ratio": Decimal("1.500"),
                "split_aces_blackjack_rule": SplitAcesBlackjackRule.NATURAL,
                "hole_card_rule": HoleCardRule.AMERICAN_PEEK,
                "insurance_enabled": True,
                "insurance_payout_ratio": Decimal("2.000"),
                "surrender_rule": SurrenderRule.LATE,
                "das_enabled": True,
                "max_resplit": 3,
                "rsa_enabled": True,
                "hit_split_aces": False,
                "charlie_rule": CharlieRule.NONE,
                "number_of_decks": 6,
                "penetration": Decimal("0.750"),
                "burn_cards": 1,
                "initial_bankroll": Decimal("1000.00"),
                "minimum_bet": Decimal("25.00"),
                "maximum_bet": Decimal("500.00"),
                "rounds_per_simulation": 50,
                "rounds_indefinite": False,
                "simulations_count": 1,
                "simulations_indefinite": False,
                "user_seed": 12345,
            }

            created_run = await repo.create_run(config_data)
            assert created_run.id is not None
            assert created_run.status == RunStatus.CREATED
            run_id = created_run.id

            # get_run
            fetched_run = await repo.get_run(run_id)
            assert fetched_run is not None
            assert fetched_run.configuration is not None
            assert fetched_run.configuration.soft_17_rule == Soft17Rule.STAND

            # list_runs
            runs_list = await repo.list_runs(limit=10, offset=0)
            assert len(runs_list) >= 1
            assert any(r.id == run_id for r in runs_list)

            # delete_run
            deleted = await repo.delete_run(run_id)
            assert deleted is True

            # Verify deletion
            assert (await repo.get_run(run_id)) is None

        await close_db()

    asyncio.run(_run())


def test_repository_round_replay():
    """Verify get_round_replay retrieves chronological ordered timeline."""
    if not DB_AVAILABLE:
        pytest.skip("PostgreSQL container is unreachable.")

    async def _run():
        session_factory = get_session_factory()
        await init_db()

        now = datetime.now(UTC)
        run_id = uuid.uuid4()

        async with session_factory() as session:
            run = Run(id=run_id, status=RunStatus.RUNNING)
            session.add(run)

            sim = Simulation(
                run_id=run.id,
                simulation_number=1,
                seed=42,
                initial_bankroll=Decimal("1000.00"),
            )
            session.add(sim)
            await session.flush()

            ps = PlayerSession(
                simulation_id=sim.id,
                player_type=PlayerType.JEV,
                initial_bankroll=Decimal("1000.00"),
                current_bankroll=Decimal("1025.00"),
            )
            session.add(ps)

            shoe = Shoe(
                simulation_id=sim.id,
                shoe_number=1,
                seed=42,
                card_order=["10S", "6H", "9D", "5C"],
                total_cards=312,
                penetration=Decimal("0.750"),
            )
            session.add(shoe)
            await session.flush()

            round_obj = Round(
                simulation_id=sim.id,
                round_number=1,
                status=RoundStatus.COMPLETED,
                dealer_final_value=19,
                started_at=now,
                finished_at=now,
            )
            session.add(round_obj)
            await session.flush()

            rp = RoundPlayer(
                round_id=round_obj.id,
                player_session_id=ps.id,
                bankroll_before=Decimal("1000.00"),
                bankroll_after=Decimal("1025.00"),
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
            )
            session.add(hand)
            await session.flush()

            # Sequential Card Events
            ce1 = CardEvent(
                round_id=round_obj.id,
                hand_id=hand.id,
                shoe_id=shoe.id,
                recipient=CardRecipient.HAND,
                event_type=CardEventType.DEAL,
                card="10S",
                sequence_number=1,
                shoe_position=0,
            )
            ce2 = CardEvent(
                round_id=round_obj.id,
                hand_id=None,
                shoe_id=shoe.id,
                recipient=CardRecipient.DEALER,
                event_type=CardEventType.DEAL,
                card="9D",
                sequence_number=2,
                shoe_position=1,
            )
            ce3 = CardEvent(
                round_id=round_obj.id,
                hand_id=hand.id,
                shoe_id=shoe.id,
                recipient=CardRecipient.HAND,
                event_type=CardEventType.DEAL,
                card="6H",
                sequence_number=3,
                shoe_position=2,
            )
            session.add_all([ce1, ce2, ce3])

            dec = Decision(
                hand_id=hand.id,
                decision_number=1,
                decision_type=DecisionType.INITIAL,
                action=PlayerAction.HIT,
                confidence_pct=Decimal("90.00"),
                running_count=0,
                true_count=Decimal("0.00"),
                bankroll_at_decision=Decimal("975.00"),
                optimal_reference_action=PlayerAction.HIT,
                agrees_with_optimal=True,
                state_snapshot={"cards": ["10S", "6H"], "dealer": "9D"},
            )
            session.add(dec)
            await session.flush()

            bet = Bet(
                round_player_id=rp.id,
                hand_id=hand.id,
                bet_type=BetType.INITIAL,
                amount=Decimal("25.00"),
            )
            session.add(bet)

            hr = HandResult(
                hand_id=hand.id,
                result=HandResultType.WIN,
                player_value=21,
                dealer_value=19,
                payout_amount=Decimal("50.00"),
                net_amount=Decimal("25.00"),
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

            repo = RunRepository(session)
            replay = await repo.get_round_replay(round_obj.id)

            assert replay is not None
            assert replay["round_id"] == str(round_obj.id)
            assert replay["round_number"] == 1
            assert replay["dealer_final_value"] == 19
            assert len(replay["cards"]) == 3
            assert replay["cards"][0]["sequence_number"] == 1
            assert replay["cards"][1]["sequence_number"] == 2
            assert replay["cards"][2]["sequence_number"] == 3

            assert len(replay["players"]) == 1
            p_data = replay["players"][0]
            assert p_data["player_type"] == "JEV"
            assert len(p_data["hands"]) == 1
            assert len(p_data["hands"][0]["decisions"]) == 1
            assert p_data["hands"][0]["decisions"][0]["action"] == "HIT"
            assert p_data["hands"][0]["result"]["result"] == "WIN"
            assert len(p_data["transactions"]) == 1

            # Cleanup
            await repo.delete_run(run_id)

        await close_db()

    asyncio.run(_run())


def test_repository_player_benchmark_summary():
    """Verify get_player_benchmark_summary dynamically computes win rates and agreement."""
    if not DB_AVAILABLE:
        pytest.skip("PostgreSQL container is unreachable.")

    async def _run():
        session_factory = get_session_factory()
        await init_db()

        run_id = uuid.uuid4()

        async with session_factory() as session:
            run = Run(id=run_id, status=RunStatus.COMPLETED)
            session.add(run)

            sim = Simulation(
                run_id=run.id,
                simulation_number=1,
                seed=42,
                initial_bankroll=Decimal("1000.00"),
                final_bankroll=Decimal("1025.00"),
            )
            session.add(sim)
            await session.flush()

            ps_opt = PlayerSession(
                simulation_id=sim.id,
                player_type=PlayerType.OPTIMAL,
                initial_bankroll=Decimal("1000.00"),
                current_bankroll=Decimal("1050.00"),
            )
            ps_jev = PlayerSession(
                simulation_id=sim.id,
                player_type=PlayerType.JEV,
                initial_bankroll=Decimal("1000.00"),
                current_bankroll=Decimal("1025.00"),
            )
            session.add_all([ps_opt, ps_jev])
            await session.flush()

            round_obj = Round(
                simulation_id=sim.id,
                round_number=1,
                status=RoundStatus.COMPLETED,
            )
            session.add(round_obj)
            await session.flush()

            # Optimal: 1 win, 1 agreeing decision
            rp_opt = RoundPlayer(
                round_id=round_obj.id,
                player_session_id=ps_opt.id,
                bankroll_before=Decimal("1000.00"),
                bankroll_after=Decimal("1050.00"),
                status=PlayerRoundStatus.RESOLVED,
            )
            session.add(rp_opt)
            await session.flush()

            hand_opt = Hand(round_player_id=rp_opt.id, hand_number=1, status=HandStatus.RESOLVED)
            session.add(hand_opt)
            await session.flush()

            dec_opt = Decision(
                hand_id=hand_opt.id,
                decision_number=1,
                decision_type=DecisionType.INITIAL,
                action=PlayerAction.STAND,
                running_count=0,
                true_count=Decimal("0.00"),
                bankroll_at_decision=Decimal("1000.00"),
                optimal_reference_action=PlayerAction.STAND,
                agrees_with_optimal=True,
                state_snapshot={},
            )
            session.add(dec_opt)
            bet_opt = Bet(round_player_id=rp_opt.id, bet_type=BetType.INITIAL, amount=Decimal("25.00"))
            session.add(bet_opt)
            hr_opt = HandResult(
                hand_id=hand_opt.id,
                result=HandResultType.WIN,
                player_value=20,
                dealer_value=18,
                payout_amount=Decimal("50.00"),
                net_amount=Decimal("25.00"),
            )
            session.add(hr_opt)

            # Jev: 1 win, 2 decisions (1 agreeing, 1 disagreeing)
            rp_jev = RoundPlayer(
                round_id=round_obj.id,
                player_session_id=ps_jev.id,
                bankroll_before=Decimal("1000.00"),
                bankroll_after=Decimal("1025.00"),
                status=PlayerRoundStatus.RESOLVED,
            )
            session.add(rp_jev)
            await session.flush()

            hand_jev = Hand(round_player_id=rp_jev.id, hand_number=1, status=HandStatus.RESOLVED)
            session.add(hand_jev)
            await session.flush()

            dec_jev1 = Decision(
                hand_id=hand_jev.id,
                decision_number=1,
                decision_type=DecisionType.INITIAL,
                action=PlayerAction.HIT,
                running_count=0,
                true_count=Decimal("0.00"),
                bankroll_at_decision=Decimal("1000.00"),
                optimal_reference_action=PlayerAction.STAND,
                agrees_with_optimal=False,
                state_snapshot={},
            )
            dec_jev2 = Decision(
                hand_id=hand_jev.id,
                decision_number=2,
                decision_type=DecisionType.AFTER_HIT,
                action=PlayerAction.STAND,
                running_count=0,
                true_count=Decimal("0.00"),
                bankroll_at_decision=Decimal("1000.00"),
                optimal_reference_action=PlayerAction.STAND,
                agrees_with_optimal=True,
                state_snapshot={},
            )
            session.add_all([dec_jev1, dec_jev2])

            bet_jev = Bet(round_player_id=rp_jev.id, bet_type=BetType.INITIAL, amount=Decimal("25.00"))
            session.add(bet_jev)
            hr_jev = HandResult(
                hand_id=hand_jev.id,
                result=HandResultType.WIN,
                player_value=21,
                dealer_value=18,
                payout_amount=Decimal("50.00"),
                net_amount=Decimal("25.00"),
            )
            session.add(hr_jev)

            await session.commit()

            repo = RunRepository(session)
            benchmarks = await repo.get_player_benchmark_summary(sim.id)

            assert len(benchmarks) == 2
            b_opt = next(b for b in benchmarks if b["player_type"] == "OPTIMAL")
            b_jev = next(b for b in benchmarks if b["player_type"] == "JEV")

            assert b_opt["agreement_pct"] == 100.0
            assert b_opt["total_wagered"] == 25.0
            assert b_opt["wins"] == 1

            assert b_jev["agreement_pct"] == 50.0
            assert b_jev["total_decisions"] == 2
            assert b_jev["optimal_decisions"] == 1
            assert b_jev["wins"] == 1

            # Cleanup
            await repo.delete_run(run_id)

        await close_db()

    asyncio.run(_run())
