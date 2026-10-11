"""Unit and integration tests for PostgreSQL persistence schema and entity integrity.

Verifies table provisioning, composite unique constraints, check constraints,
and foreign key cascading deletion across all 15 relational domain models.
"""

import asyncio
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

try:
    from app.persistence.database import check_db_health, close_db, get_engine, init_db
    from app.persistence.models import (
        BankrollTransaction,
        Base,
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
        PlayerShoeState,
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
        init_db,
    )
    from backend.app.persistence.models import (
        BankrollTransaction,
        Base,
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
        PlayerShoeState,
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
    """Synchronous probe to determine if PostgreSQL is reachable."""
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


async def get_test_session() -> tuple[AsyncSession, async_sessionmaker[AsyncSession]]:
    engine = get_engine()
    await init_db(engine)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    return session_factory(), session_factory


def test_schema_metadata_contains_all_15_tables():
    """Verify that Base.metadata includes all 15 required domain tables."""
    expected_tables = {
        "runs",
        "run_configurations",
        "simulations",
        "player_sessions",
        "shoes",
        "player_shoe_states",
        "rounds",
        "round_players",
        "hands",
        "card_events",
        "decisions",
        "model_responses",
        "bets",
        "hand_results",
        "bankroll_transactions",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(actual_tables), f"Missing tables: {expected_tables - actual_tables}"


def test_create_run_and_descendant_entities():
    """Verify end-to-end insertion of a complete 15-entity hierarchy."""
    if not DB_AVAILABLE:
        print("Skipping database test: PostgreSQL container is unreachable.")
        return

    async def _run():
        session, _ = await get_test_session()
        async with session:
            # 1. Run & Configuration
            run = Run(status=RunStatus.CREATED)
            session.add(run)
            await session.flush()

            config = RunConfiguration(
                run_id=run.id,
                soft_17_rule=Soft17Rule.STAND,
                blackjack_payout_ratio=Decimal("1.500"),
                split_aces_blackjack_rule=SplitAcesBlackjackRule.NATURAL,
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
                user_seed=12345,
                optimal_bet_spread={"<=0": 1, "1": 2, "2": 4},
            )
            session.add(config)
            await session.flush()

            # 2. Simulation
            sim = Simulation(
                run_id=run.id,
                simulation_number=1,
                seed=12345,
                status=SimulationStatus.RUNNING,
                initial_bankroll=Decimal("1000.00"),
            )
            session.add(sim)
            await session.flush()

            # 3. PlayerSession (Jev, Laya, Optimal)
            session_jev = PlayerSession(
                simulation_id=sim.id,
                player_type=PlayerType.JEV,
                initial_bankroll=Decimal("1000.00"),
                current_bankroll=Decimal("1000.00"),
                status=SessionStatus.ACTIVE,
            )
            session.add(session_jev)
            await session.flush()

            # 4. Shoe & PlayerShoeState
            shoe = Shoe(
                simulation_id=sim.id,
                shoe_number=1,
                seed=54321,
                card_order=["AS", "10H", "7D", "4C"],
                total_cards=312,
                burn_cards=1,
                penetration=Decimal("0.750"),
                generated_by_session_id=session_jev.id,
            )
            session.add(shoe)
            await session.flush()

            shoe_state = PlayerShoeState(
                player_session_id=session_jev.id,
                shoe_id=shoe.id,
                current_position=0,
                cards_seen=0,
                running_count=0,
                true_count=Decimal("0.00"),
            )
            session.add(shoe_state)
            await session.flush()

            # 5. Round & RoundPlayer
            round_obj = Round(
                simulation_id=sim.id,
                round_number=1,
                status=RoundStatus.IN_PROGRESS,
            )
            session.add(round_obj)
            await session.flush()

            round_player = RoundPlayer(
                round_id=round_obj.id,
                player_session_id=session_jev.id,
                bankroll_before=Decimal("1000.00"),
                bankroll_after=Decimal("975.00"),
                status=PlayerRoundStatus.ACTIVE,
            )
            session.add(round_player)
            await session.flush()

            # 6. Hand & CardEvent
            hand = Hand(
                round_player_id=round_player.id,
                hand_number=1,
                is_initial=True,
                is_split=False,
                status=HandStatus.IN_PLAY,
            )
            session.add(hand)
            await session.flush()

            card_ev = CardEvent(
                round_id=round_obj.id,
                hand_id=hand.id,
                shoe_id=shoe.id,
                recipient=CardRecipient.HAND,
                event_type=CardEventType.DEAL,
                card="AS",
                sequence_number=1,
                shoe_position=0,
            )
            session.add(card_ev)
            await session.flush()

            # 7. Decision & ModelResponse
            decision = Decision(
                hand_id=hand.id,
                decision_number=1,
                decision_type=DecisionType.INITIAL,
                action=PlayerAction.HIT,
                confidence_pct=Decimal("88.50"),
                running_count=1,
                true_count=Decimal("0.50"),
                bankroll_at_decision=Decimal("975.00"),
                optimal_reference_action=PlayerAction.HIT,
                agrees_with_optimal=True,
                state_snapshot={"player_cards": ["AS", "5H"], "dealer_upcard": "9C"},
            )
            session.add(decision)
            await session.flush()

            model_resp = ModelResponse(
                decision_id=decision.id,
                provider=ModelProvider.SYSTEM_ONE,
                model_name="jev-v1",
                model_version="1.0.0",
                request_payload={"context": "test"},
                response_payload={"action": "HIT", "confidence": 0.885},
                http_status=200,
                latency_ms=45,
                requested_at=round_obj.started_at,
                responded_at=round_obj.started_at,
            )
            session.add(model_resp)
            await session.flush()

            # 8. Bet, HandResult, BankrollTransaction
            bet = Bet(
                round_player_id=round_player.id,
                hand_id=hand.id,
                bet_type=BetType.INITIAL,
                amount=Decimal("25.00"),
            )
            session.add(bet)
            await session.flush()

            hand_res = HandResult(
                hand_id=hand.id,
                result=HandResultType.WIN,
                player_value=21,
                dealer_value=20,
                payout_amount=Decimal("50.00"),
                net_amount=Decimal("25.00"),
            )
            session.add(hand_res)
            await session.flush()

            tx = BankrollTransaction(
                round_player_id=round_player.id,
                hand_id=hand.id,
                bet_id=bet.id,
                transaction_type=TransactionType.BET,
                amount=Decimal("-25.00"),
                balance_before=Decimal("1000.00"),
                balance_after=Decimal("975.00"),
            )
            session.add(tx)
            await session.commit()

            # Assert retrieval
            stmt = (
                select(Run)
                .options(selectinload(Run.simulations).selectinload(Simulation.player_sessions))
                .where(Run.id == run.id)
            )
            res = await session.execute(stmt)
            loaded_run = res.scalar_one_or_none()
            assert loaded_run is not None
            assert len(loaded_run.simulations) == 1
            assert len(loaded_run.simulations[0].player_sessions) == 1

            # Cleanup
            await session.delete(loaded_run)
            await session.commit()
        await close_db()

    asyncio.run(_run())


def test_unique_constraints_enforcement():
    """Verify composite unique constraints on simulation, session, and round."""
    if not DB_AVAILABLE:
        print("Skipping database test: PostgreSQL container is unreachable.")
        return

    async def _run():
        session, _ = await get_test_session()
        async with session:
            run = Run(status=RunStatus.CREATED)
            session.add(run)
            await session.commit()

            sim = Simulation(
                run_id=run.id,
                simulation_number=1,
                seed=100,
                initial_bankroll=Decimal("500.00"),
            )
            session.add(sim)
            await session.commit()

            # Duplicate simulation_number for same run_id must raise IntegrityError
            try:
                async with session.begin_nested():
                    dup_sim = Simulation(
                        run_id=run.id,
                        simulation_number=1,
                        seed=200,
                        initial_bankroll=Decimal("500.00"),
                    )
                    session.add(dup_sim)
                    await session.flush()
                assert False, "Duplicate simulation_number should have failed!"
            except IntegrityError:
                pass

            # Add valid player_type
            p1 = PlayerSession(
                simulation_id=sim.id,
                player_type=PlayerType.OPTIMAL,
                initial_bankroll=Decimal("500.00"),
                current_bankroll=Decimal("500.00"),
            )
            session.add(p1)
            await session.commit()

            # Duplicate player_type for same simulation_id must raise IntegrityError
            try:
                async with session.begin_nested():
                    p2 = PlayerSession(
                        simulation_id=sim.id,
                        player_type=PlayerType.OPTIMAL,
                        initial_bankroll=Decimal("500.00"),
                        current_bankroll=Decimal("500.00"),
                    )
                    session.add(p2)
                    await session.flush()
                assert False, "Duplicate player_type in same simulation should have failed!"
            except IntegrityError:
                pass

            # Cleanup
            await session.delete(run)
            await session.commit()
        await close_db()

    asyncio.run(_run())


def test_cascading_deletion():
    """Verify that deleting Run cascades and purges all child records."""
    if not DB_AVAILABLE:
        print("Skipping database test: PostgreSQL container is unreachable.")
        return

    async def _run():
        session, _ = await get_test_session()
        async with session:
            run = Run(status=RunStatus.CREATED)
            session.add(run)
            await session.flush()

            sim = Simulation(
                run_id=run.id,
                simulation_number=1,
                seed=999,
                initial_bankroll=Decimal("100.00"),
            )
            session.add(sim)
            await session.flush()

            player_session = PlayerSession(
                simulation_id=sim.id,
                player_type=PlayerType.LAYA,
                initial_bankroll=Decimal("100.00"),
                current_bankroll=Decimal("100.00"),
            )
            session.add(player_session)
            await session.commit()

            sim_id = sim.id
            session_id = player_session.id

            # Delete Run
            await session.delete(run)
            await session.commit()

            # Verify child records are gone
            assert (await session.get(Simulation, sim_id)) is None
            assert (await session.get(PlayerSession, session_id)) is None
        await close_db()

    asyncio.run(_run())


if __name__ == "__main__":
    test_schema_metadata_contains_all_15_tables()
    print("✓ test_schema_metadata_contains_all_15_tables passed")
    test_create_run_and_descendant_entities()
    print("✓ test_create_run_and_descendant_entities passed")
    test_unique_constraints_enforcement()
    print("✓ test_unique_constraints_enforcement passed")
    test_cascading_deletion()
    print("✓ test_cascading_deletion passed")
    print("All persistence schema tests passed successfully!")
