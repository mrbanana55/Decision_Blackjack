"""Telemetry persistence listener for simulation events.

Subscribes to the orchestrator's asynchronous EventEmitter stream and persists
card events, decisions, model responses, bets, and ledger transactions to PostgreSQL.
Enforces atomic round-boundary batch commits and error-state capture.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .database import get_session_factory
from .models import (
    BankrollTransaction,
    Bet,
    BetType,
    CardEvent,
    CardEventType,
    CardRecipient,
    Decision,
    DecisionType,
    Hand,
    HandResult,
    HandResultType,
    HandStatus,
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
    RunStatus,
    SessionStatus,
    Shoe,
    Simulation,
    SimulationStatus,
    TerminationReason,
    TransactionType,
)

try:
    from app.simulation.events import EventEmitter, EventType, SimulationEvent
except ImportError:
    from backend.app.simulation.events import EventEmitter, EventType, SimulationEvent

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class SimulationPersistenceListener:
    """Asynchronous listener persisting simulation event telemetry to PostgreSQL."""

    def __init__(
        self,
        run_id: uuid.UUID,
        event_emitter: EventEmitter,
        batch_rounds: int = 1,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        """Initialize listener attached to an EventEmitter and run ID.

        Args:
            run_id: Top-level experiment Run UUID.
            event_emitter: Orchestrator event dispatcher.
            batch_rounds: Number of completed rounds before committing (1 = per-round flush).
            session_factory: AsyncSession factory, defaults to singleton.
        """
        self.run_id = run_id
        self.event_emitter = event_emitter
        self.batch_rounds = max(1, batch_rounds)
        self.session_factory = session_factory or get_session_factory()

        # In-memory tracking state
        self._sim_id: uuid.UUID | None = None
        self._sim_number: int = 1
        self._player_sessions: dict[str, PlayerSession] = {}
        self._current_shoe: Shoe | None = None
        self._shoe_states: dict[str, PlayerShoeState] = {}
        self._current_round: Round | None = None
        self._round_players: dict[str, RoundPlayer] = {}
        self._active_hands: dict[str, list[Hand]] = {}
        self._card_sequence: int = 1
        self._shoe_position: int = 0
        self._round_buffer_count: int = 0
        self._session: AsyncSession | None = None
        self._lock: asyncio.Lock = asyncio.Lock()
        self._is_attached: bool = False

    def attach(self) -> None:
        """Register listeners for orchestrator event types."""
        if not self._is_attached:
            self.event_emitter.subscribe(None, self.handle_event)
            self._is_attached = True

    def detach(self) -> None:
        """Unsubscribe from event emitter."""
        if self._is_attached:
            self.event_emitter.unsubscribe(None, self.handle_event)
            self._is_attached = False

    async def _get_session(self) -> AsyncSession:
        """Ensure an active database session exists."""
        if self._session is None:
            self._session = self.session_factory()
        return self._session

    async def flush(self) -> None:
        """Explicitly flush and commit any pending buffered records to PostgreSQL."""
        if self._session is not None:
            try:
                await self._session.commit()
                self._round_buffer_count = 0
            except Exception as e:
                logger.error(f"Error flushing simulation persistence session: {e}")
                await self._session.rollback()
                raise
            finally:
                await self._session.close()
                self._session = None

    async def _ensure_run_and_simulation(
        self,
        session: AsyncSession,
        seed: int = 42,
        initial_bankroll: Decimal = Decimal("1000.00"),
    ) -> Simulation:
        """Ensure Run, Simulation, and base Shoe exist in PostgreSQL."""
        if self._sim_id is not None:
            sim = await session.get(Simulation, self._sim_id)
            if sim:
                return sim

        # 1. Ensure Run exists
        run = await session.get(Run, self.run_id)
        if run is None:
            run = Run(
                id=self.run_id,
                status=RunStatus.RUNNING,
                started_at=_utcnow(),
            )
            session.add(run)
            await session.flush()
        elif run.status == RunStatus.CREATED:
            run.status = RunStatus.RUNNING
            run.started_at = _utcnow()
            await session.flush()

        # 2. Ensure Simulation exists
        stmt = select(Simulation).where(
            Simulation.run_id == self.run_id,
            Simulation.simulation_number == self._sim_number,
        )
        res = await session.execute(stmt)
        sim = res.scalar_one_or_none()
        if sim is None:
            sim = Simulation(
                run_id=self.run_id,
                simulation_number=self._sim_number,
                seed=seed,
                initial_bankroll=initial_bankroll,
                status=SimulationStatus.RUNNING,
                started_at=_utcnow(),
            )
            session.add(sim)
            await session.flush()

        self._sim_id = sim.id

        # 3. Ensure base Shoe exists
        if self._current_shoe is None:
            shoe_stmt = select(Shoe).where(
                Shoe.simulation_id == sim.id,
                Shoe.shoe_number == 1,
            )
            shoe_res = await session.execute(shoe_stmt)
            shoe = shoe_res.scalar_one_or_none()
            if shoe is None:
                shoe = Shoe(
                    simulation_id=sim.id,
                    shoe_number=1,
                    seed=seed,
                    card_order=[],
                    total_cards=312,
                    penetration=Decimal("0.750"),
                )
                session.add(shoe)
                await session.flush()
            self._current_shoe = shoe

        return sim

    async def _ensure_player_session(
        self,
        session: AsyncSession,
        entity_id: str,
        bankroll: Decimal = Decimal("1000.00"),
    ) -> PlayerSession:
        """Ensure PlayerSession exists for the given entity ID."""
        eid = entity_id.lower().strip()
        if eid in self._player_sessions:
            return self._player_sessions[eid]

        if "jev" in eid:
            ptype = PlayerType.JEV
        elif "laya" in eid:
            ptype = PlayerType.LAYA
        else:
            ptype = PlayerType.OPTIMAL

        stmt = select(PlayerSession).where(
            PlayerSession.simulation_id == self._sim_id,
            PlayerSession.player_type == ptype,
        )
        res = await session.execute(stmt)
        ps = res.scalar_one_or_none()

        if ps is None:
            ps = PlayerSession(
                simulation_id=self._sim_id,
                player_type=ptype,
                initial_bankroll=bankroll,
                current_bankroll=bankroll,
                status=SessionStatus.ACTIVE,
            )
            session.add(ps)
            await session.flush()

        self._player_sessions[eid] = ps

        # Ensure PlayerShoeState exists for current shoe
        if self._current_shoe and eid not in self._shoe_states:
            pss_stmt = select(PlayerShoeState).where(
                PlayerShoeState.player_session_id == ps.id,
                PlayerShoeState.shoe_id == self._current_shoe.id,
            )
            pss_res = await session.execute(pss_stmt)
            pss = pss_res.scalar_one_or_none()
            if pss is None:
                pss = PlayerShoeState(
                    player_session_id=ps.id,
                    shoe_id=self._current_shoe.id,
                    current_position=0,
                    cards_seen=0,
                    running_count=0,
                    true_count=Decimal("0.00"),
                )
                session.add(pss)
                await session.flush()
            self._shoe_states[eid] = pss

        return ps

    async def handle_event(self, event: SimulationEvent) -> None:
        """Route incoming simulation event to its persistence handler."""
        async with self._lock:
            session = await self._get_session()
            event_type = event.event_type

            if event_type == EventType.SESSION_STARTED:
                await self._handle_session_started(session, event)
            elif event_type == EventType.SHOE_RESHUFFLED:
                await self._handle_shoe_reshuffled(session, event)
            elif event_type == EventType.ROUND_STARTED:
                await self._handle_round_started(session, event)
            elif event_type == EventType.CARD_DEALT:
                await self._handle_card_dealt(session, event)
            elif event_type == EventType.DECISION_APPLIED:
                await self._handle_decision_applied(session, event)
            elif event_type == EventType.ROUND_SETTLED:
                await self._handle_round_settled(session, event)
            elif event_type == EventType.SESSION_COMPLETED:
                await self._handle_session_completed(session, event)
            elif event_type == EventType.SESSION_STOPPED:
                await self._handle_session_stopped(session, event)
            elif event_type == EventType.SESSION_ERROR:
                await self._handle_session_error(session, event)

    async def _handle_session_started(self, session: AsyncSession, event: SimulationEvent) -> None:
        seed = int(event.payload.get("seed", 42))
        bankroll = Decimal(str(event.payload.get("initial_bankroll", 1000.0)))
        await self._ensure_run_and_simulation(session, seed, bankroll)

        entities = event.payload.get("entities", [])
        for eid in entities:
            await self._ensure_player_session(session, str(eid), bankroll)

    async def _handle_shoe_reshuffled(self, session: AsyncSession, event: SimulationEvent) -> None:
        if self._sim_id is None:
            await self._ensure_run_and_simulation(session)

        gen = int(event.payload.get("generation", 1))
        shoe = Shoe(
            simulation_id=self._sim_id,
            shoe_number=gen + 1,
            seed=gen,
            card_order=[],
            total_cards=312,
            penetration=Decimal("0.750"),
        )
        session.add(shoe)
        await session.flush()
        self._current_shoe = shoe
        self._shoe_states.clear()
        self._shoe_position = 0

        # Create PlayerShoeState for each player
        for eid, ps in self._player_sessions.items():
            pss = PlayerShoeState(
                player_session_id=ps.id,
                shoe_id=shoe.id,
                current_position=0,
                cards_seen=0,
                running_count=0,
                true_count=Decimal("0.00"),
            )
            session.add(pss)
            await session.flush()
            self._shoe_states[eid] = pss

    async def _handle_round_started(self, session: AsyncSession, event: SimulationEvent) -> None:
        if self._sim_id is None:
            await self._ensure_run_and_simulation(session)

        round_num = int(event.payload.get("round_number", 1))

        # Check if Round already exists
        stmt = select(Round).where(
            Round.simulation_id == self._sim_id,
            Round.round_number == round_num,
        )
        res = await session.execute(stmt)
        round_obj = res.scalar_one_or_none()

        if round_obj is None:
            round_obj = Round(
                simulation_id=self._sim_id,
                round_number=round_num,
                status=RoundStatus.IN_PROGRESS,
                started_at=_utcnow(),
            )
            session.add(round_obj)
            await session.flush()

        self._current_round = round_obj
        self._card_sequence = 1
        self._round_players.clear()
        self._active_hands.clear()

        active_entities = event.payload.get("active_entities", [])
        min_bet = Decimal(str(event.payload.get("min_bet", 25.0)))

        for entity_id in active_entities:
            eid = str(entity_id).lower()
            ps = await self._ensure_player_session(session, eid)

            rp = RoundPlayer(
                round_id=round_obj.id,
                player_session_id=ps.id,
                bankroll_before=ps.current_bankroll,
                bankroll_after=ps.current_bankroll - min_bet,
                status=PlayerRoundStatus.ACTIVE,
                started_at=_utcnow(),
            )
            session.add(rp)
            await session.flush()
            self._round_players[eid] = rp

            # Initial hand
            hand = Hand(
                round_player_id=rp.id,
                hand_number=1,
                is_initial=True,
                is_split=False,
                status=HandStatus.IN_PLAY,
            )
            session.add(hand)
            await session.flush()
            self._active_hands[eid] = [hand]

            # Initial bet & transaction
            bet = Bet(
                round_player_id=rp.id,
                hand_id=hand.id,
                bet_type=BetType.INITIAL,
                amount=min_bet,
            )
            session.add(bet)
            await session.flush()

            tx = BankrollTransaction(
                round_player_id=rp.id,
                hand_id=hand.id,
                bet_id=bet.id,
                transaction_type=TransactionType.BET,
                amount=-min_bet,
                balance_before=ps.current_bankroll,
                balance_after=ps.current_bankroll - min_bet,
            )
            session.add(tx)
            ps.current_bankroll -= min_bet

    async def _handle_card_dealt(self, session: AsyncSession, event: SimulationEvent) -> None:
        if self._current_round is None:
            return

        shoe_id = self._current_shoe.id if self._current_shoe else None
        if shoe_id is None:
            return

        entity_id = event.payload.get("entity_id")
        player_cards = event.payload.get("player_cards")
        dealer_upcard = event.payload.get("dealer_upcard")

        # Dealing player cards
        if player_cards and entity_id:
            eid = str(entity_id).lower()
            hands = self._active_hands.get(eid, [])
            hand_id = hands[0].id if hands else None

            for card_str in player_cards:
                ce = CardEvent(
                    round_id=self._current_round.id,
                    hand_id=hand_id,
                    shoe_id=shoe_id,
                    recipient=CardRecipient.HAND,
                    event_type=CardEventType.DEAL,
                    card=str(card_str),
                    sequence_number=self._card_sequence,
                    shoe_position=self._shoe_position,
                )
                self._card_sequence += 1
                self._shoe_position += 1
                session.add(ce)

        # Dealing dealer upcard
        if dealer_upcard:
            ce = CardEvent(
                round_id=self._current_round.id,
                hand_id=None,
                shoe_id=shoe_id,
                recipient=CardRecipient.DEALER,
                event_type=CardEventType.DEAL,
                card=str(dealer_upcard),
                sequence_number=self._card_sequence,
                shoe_position=self._shoe_position,
            )
            self._card_sequence += 1
            self._shoe_position += 1
            session.add(ce)

        # Single card dealt event
        single_card = event.payload.get("card")
        if single_card:
            recipient_str = str(event.payload.get("recipient", "HAND")).upper()
            recipient = CardRecipient[recipient_str] if recipient_str in CardRecipient.__members__ else CardRecipient.HAND
            ce = CardEvent(
                round_id=self._current_round.id,
                hand_id=event.payload.get("hand_id"),
                shoe_id=shoe_id,
                recipient=recipient,
                event_type=CardEventType.DEAL,
                card=str(single_card),
                sequence_number=self._card_sequence,
                shoe_position=self._shoe_position,
            )
            self._card_sequence += 1
            self._shoe_position += 1
            session.add(ce)

    async def _handle_decision_applied(self, session: AsyncSession, event: SimulationEvent) -> None:
        entity_id = str(event.payload.get("entity_id", "optimal")).lower()
        hands = self._active_hands.get(entity_id, [])
        if not hands:
            return
        hand = hands[0]

        # Action resolution
        action_raw = str(event.payload.get("action", "STAND")).upper()
        action = PlayerAction[action_raw] if action_raw in PlayerAction.__members__ else PlayerAction.STAND

        # Optimal reference action
        comparison = event.payload.get("comparison", {})
        optimal_raw = str(comparison.get("optimal_action", action_raw)).upper()
        optimal_action = PlayerAction[optimal_raw] if optimal_raw in PlayerAction.__members__ else action
        agrees = bool(comparison.get("is_optimal", comparison.get("agrees_with_optimal", True)))

        # Confidence percentage [0..100]
        conf_raw = event.payload.get("confidence")
        if conf_raw is not None:
            c_float = float(conf_raw)
            confidence_pct = Decimal(str(round(c_float * 100.0 if c_float <= 1.0 else c_float, 2)))
        else:
            confidence_pct = Decimal("100.00")

        # Snapshot & counts
        ps = self._player_sessions.get(entity_id)
        bankroll = ps.current_bankroll if ps else Decimal("1000.00")
        snapshot = event.payload.get(
            "state_snapshot",
            {
                "action": action.value,
                "confidence": float(confidence_pct),
                "reasoning": event.payload.get("reasoning", ""),
            },
        )

        dec_count_stmt = select(Decision).where(Decision.hand_id == hand.id)
        dec_res = await session.execute(dec_count_stmt)
        existing_decs = dec_res.scalars().all()
        dec_num = len(existing_decs) + 1
        dec_type = DecisionType.INITIAL if dec_num == 1 else DecisionType.AFTER_HIT

        decision = Decision(
            hand_id=hand.id,
            decision_number=dec_num,
            decision_type=dec_type,
            action=action,
            confidence_pct=confidence_pct,
            running_count=int(event.payload.get("running_count", 0)),
            true_count=Decimal(str(event.payload.get("true_count", 0.0))),
            bankroll_at_decision=bankroll,
            optimal_reference_action=optimal_action,
            agrees_with_optimal=agrees,
            state_snapshot=snapshot,
        )
        session.add(decision)
        await session.flush()

        # Check for AI Model Response auditing
        model_name = event.payload.get("model_name")
        model_provider_raw = event.payload.get("model_provider")
        latency_ms = round(float(event.payload.get("latency_ms", 0.0)))

        if model_name or model_provider_raw or entity_id in ("jev", "laya"):
            if model_provider_raw and str(model_provider_raw).upper() in ModelProvider.__members__:
                provider = ModelProvider[str(model_provider_raw).upper()]
            elif "jev" in entity_id:
                provider = ModelProvider.SYSTEM_ONE
            else:
                provider = ModelProvider.LOCAL_MODEL

            now = _utcnow()
            mr = ModelResponse(
                decision_id=decision.id,
                provider=provider,
                model_name=str(model_name or f"{entity_id}-agent"),
                model_version=event.payload.get("model_version"),
                request_payload=event.payload.get("request_payload", {"entity_id": entity_id}),
                response_payload=event.payload.get(
                    "response_payload",
                    {"action": action.value, "confidence": float(confidence_pct)},
                ),
                http_status=int(event.payload.get("http_status", 200)),
                latency_ms=latency_ms,
                requested_at=now,
                responded_at=now,
            )
            session.add(mr)

    async def _handle_round_settled(self, session: AsyncSession, event: SimulationEvent) -> None:
        entity_id = str(event.payload.get("entity_id", "optimal")).lower()
        rp = self._round_players.get(entity_id)
        ps = self._player_sessions.get(entity_id)
        hands = self._active_hands.get(entity_id, [])
        hand = hands[0] if hands else None

        final_bankroll = Decimal(str(event.payload.get("final_bankroll", 1000.0)))
        net_profit = Decimal(str(event.payload.get("net_profit", 0.0)))
        outcomes = event.payload.get("outcomes", [])

        if hand:
            if outcomes:
                for ho in outcomes:
                    res_raw = str(ho.get("outcome", "win")).upper()
                    result_type = HandResultType[res_raw] if res_raw in HandResultType.__members__ else HandResultType.WIN
                    ho_net = Decimal(str(ho.get("net_profit", net_profit)))
                    payout = ho_net + Decimal("25.00") if ho_net > 0 else (Decimal("25.00") if ho_net == 0 else Decimal("0.00"))
                    hr = HandResult(
                        hand_id=hand.id,
                        result=result_type,
                        player_value=int(ho.get("player_value", 20)),
                        dealer_value=int(ho.get("dealer_value", 20)),
                        payout_amount=payout,
                        net_amount=ho_net,
                    )
                    session.add(hr)
            else:
                result_type = HandResultType.WIN if net_profit > 0 else (HandResultType.LOSS if net_profit < 0 else HandResultType.PUSH)
                payout = net_profit + Decimal("25.00") if net_profit > 0 else (Decimal("25.00") if net_profit == 0 else Decimal("0.00"))
                hr = HandResult(
                    hand_id=hand.id,
                    result=result_type,
                    player_value=20,
                    dealer_value=20,
                    payout_amount=payout,
                    net_amount=net_profit,
                )
                session.add(hr)

            hand.status = HandStatus.RESOLVED

        if rp and ps:
            # Payout / settlement transaction
            balance_change = final_bankroll - rp.bankroll_after if rp.bankroll_after != None else final_bankroll
            if balance_change != Decimal("0.00"):
                tx_type = TransactionType.PAYOUT if balance_change > Decimal("0.00") else TransactionType.BET
                tx = BankrollTransaction(
                    round_player_id=rp.id,
                    hand_id=hand.id if hand else None,
                    transaction_type=tx_type,
                    amount=balance_change,
                    balance_before=rp.bankroll_after,
                    balance_after=final_bankroll,
                )
                session.add(tx)

            rp.bankroll_after = final_bankroll
            rp.status = PlayerRoundStatus.RESOLVED
            rp.finished_at = _utcnow()
            ps.current_bankroll = final_bankroll

        # Check if all round players have settled
        all_resolved = all(p.status == PlayerRoundStatus.RESOLVED for p in self._round_players.values())
        if all_resolved and self._current_round:
            self._current_round.status = RoundStatus.COMPLETED
            self._current_round.finished_at = _utcnow()
            self._round_buffer_count += 1

            if self._round_buffer_count >= self.batch_rounds:
                await self.flush()

    async def _handle_session_completed(self, session: AsyncSession, event: SimulationEvent) -> None:
        if self._sim_id:
            sim = await session.get(Simulation, self._sim_id)
            if sim:
                sim.status = SimulationStatus.COMPLETED
                sim.termination_reason = TerminationReason.ROUNDS_COMPLETED
                sim.finished_at = _utcnow()

        run = await session.get(Run, self.run_id)
        if run:
            run.status = RunStatus.COMPLETED
            run.finished_at = _utcnow()

        await self.flush()

    async def _handle_session_stopped(self, session: AsyncSession, event: SimulationEvent) -> None:
        if self._sim_id:
            sim = await session.get(Simulation, self._sim_id)
            if sim:
                sim.status = SimulationStatus.CANCELLED
                sim.termination_reason = TerminationReason.USER_STOPPED
                sim.finished_at = _utcnow()

        run = await session.get(Run, self.run_id)
        if run:
            run.status = RunStatus.CANCELLED
            run.finished_at = _utcnow()

        await self.flush()

    async def _handle_session_error(self, session: AsyncSession, event: SimulationEvent) -> None:
        error_msg = str(event.payload.get("error", "Unknown simulation fault"))

        if self._sim_id:
            sim = await session.get(Simulation, self._sim_id)
            if sim:
                sim.status = SimulationStatus.ERROR
                sim.termination_reason = TerminationReason.ERROR
                sim.finished_at = _utcnow()

        run = await session.get(Run, self.run_id)
        if run:
            run.status = RunStatus.ERROR
            run.error_message = error_msg
            run.finished_at = _utcnow()

        await self.flush()
