"""Data access repository for simulation experiments, chronological replays, and benchmarks.

Provides CRUD operations, cascading deletions, chronological round timeline queries,
and dynamic analytical benchmark calculations.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    CharlieRule,
    Decision,
    Hand,
    HandResultType,
    HoleCardRule,
    PlayerSession,
    Round,
    RoundPlayer,
    Run,
    RunConfiguration,
    RunStatus,
    Simulation,
    Soft17Rule,
    SplitAcesBlackjackRule,
    SurrenderRule,
)


class RunRepository:
    """Data access repository for simulation experiments and historical replays."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize RunRepository with active database session.

        Args:
            session: Async database session.
        """
        self.session = session

    async def create_run(self, config_dict: dict[str, Any]) -> Run:
        """Create a new Run and its immutable RunConfiguration snapshot.

        Args:
            config_dict: Dictionary containing simulation and table rules.

        Returns:
            The newly created Run entity.
        """
        run = Run(status=RunStatus.CREATED)
        self.session.add(run)
        await self.session.flush()

        # Parse or default config parameters
        soft_17 = config_dict.get("soft_17_rule", Soft17Rule.STAND)
        if isinstance(soft_17, str):
            soft_17 = Soft17Rule[soft_17.upper()]

        split_aces = config_dict.get("split_aces_blackjack_rule", SplitAcesBlackjackRule.NATURAL)
        if isinstance(split_aces, str):
            split_aces = SplitAcesBlackjackRule[split_aces.upper()]

        hole_card = config_dict.get("hole_card_rule", HoleCardRule.AMERICAN_PEEK)
        if isinstance(hole_card, str):
            hole_card = HoleCardRule[hole_card.upper()]

        surrender = config_dict.get("surrender_rule", SurrenderRule.LATE)
        if isinstance(surrender, str):
            surrender = SurrenderRule[surrender.upper()]

        charlie = config_dict.get("charlie_rule", CharlieRule.NONE)
        if isinstance(charlie, str):
            charlie = CharlieRule[charlie.upper()]

        cfg = RunConfiguration(
            run_id=run.id,
            soft_17_rule=soft_17,
            blackjack_payout_ratio=Decimal(str(config_dict.get("blackjack_payout_ratio", "1.500"))),
            split_aces_blackjack_rule=split_aces,
            hole_card_rule=hole_card,
            insurance_enabled=bool(config_dict.get("insurance_enabled", True)),
            insurance_payout_ratio=Decimal(str(config_dict.get("insurance_payout_ratio", "2.000"))),
            surrender_rule=surrender,
            das_enabled=bool(config_dict.get("das_enabled", True)),
            max_resplit=int(config_dict.get("max_resplit", 3)),
            rsa_enabled=bool(config_dict.get("rsa_enabled", False)),
            hit_split_aces=bool(config_dict.get("hit_split_aces", False)),
            charlie_rule=charlie,
            number_of_decks=int(config_dict.get("number_of_decks", 6)),
            penetration=Decimal(str(config_dict.get("penetration", "0.750"))),
            burn_cards=int(config_dict.get("burn_cards", 1)),
            initial_bankroll=Decimal(str(config_dict.get("initial_bankroll", "1000.00"))),
            minimum_bet=Decimal(str(config_dict.get("minimum_bet", "25.00"))),
            maximum_bet=Decimal(str(config_dict.get("maximum_bet", "500.00"))),
            rounds_per_simulation=int(config_dict.get("rounds_per_simulation", 100)),
            rounds_indefinite=bool(config_dict.get("rounds_indefinite", False)),
            simulations_count=int(config_dict.get("simulations_count", 1)),
            simulations_indefinite=bool(config_dict.get("simulations_indefinite", False)),
            user_seed=config_dict.get("user_seed"),
            optimal_bet_spread=config_dict.get("optimal_bet_spread"),
        )
        self.session.add(cfg)
        await self.session.commit()

        # Eager load configuration
        stmt = select(Run).options(selectinload(Run.configuration)).where(Run.id == run.id)
        res = await self.session.execute(stmt)
        return res.scalar_one()

    async def get_run(self, run_id: uuid.UUID) -> Run | None:
        """Retrieve a Run with its configuration and simulations."""
        stmt = (
            select(Run)
            .options(
                selectinload(Run.configuration),
                selectinload(Run.simulations).selectinload(Simulation.rounds),
                selectinload(Run.simulations).selectinload(Simulation.player_sessions),
            )
            .where(Run.id == run_id)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_runs(self, limit: int = 50, offset: int = 0) -> list[Run]:
        """List past runs ordered by created_at descending."""
        stmt = (
            select(Run)
            .options(selectinload(Run.configuration))
            .order_by(Run.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def delete_run(self, run_id: uuid.UUID) -> bool:
        """Cascading-delete a Run and all its descendant records."""
        run = await self.session.get(Run, run_id)
        if run is None:
            return False

        await self.session.delete(run)
        await self.session.commit()
        return True

    async def get_round_replay(self, round_id: uuid.UUID) -> dict[str, Any] | None:
        """Retrieve full chronological timeline of a round (cards, decisions, bankroll ledger)."""
        stmt = (
            select(Round)
            .options(
                selectinload(Round.card_events),
                selectinload(Round.round_players)
                .selectinload(RoundPlayer.player_session),
                selectinload(Round.round_players)
                .selectinload(RoundPlayer.bets),
                selectinload(Round.round_players)
                .selectinload(RoundPlayer.transactions),
                selectinload(Round.round_players)
                .selectinload(RoundPlayer.hands)
                .selectinload(Hand.decisions)
                .selectinload(Decision.model_response),
                selectinload(Round.round_players)
                .selectinload(RoundPlayer.hands)
                .selectinload(Hand.result),
            )
            .where(Round.id == round_id)
        )
        res = await self.session.execute(stmt)
        round_obj = res.scalar_one_or_none()
        if round_obj is None:
            return None

        # Sorted card events
        cards = [
            {
                "id": str(ce.id),
                "sequence_number": ce.sequence_number,
                "recipient": ce.recipient.value,
                "card": ce.card,
                "shoe_position": ce.shoe_position,
                "hand_id": str(ce.hand_id) if ce.hand_id else None,
                "created_at": ce.created_at.isoformat(),
            }
            for ce in sorted(round_obj.card_events, key=lambda c: c.sequence_number)
        ]

        players = []
        for rp in round_obj.round_players:
            hands = []
            for h in rp.hands:
                decisions = [
                    {
                        "id": str(d.id),
                        "decision_number": d.decision_number,
                        "decision_type": d.decision_type.value,
                        "action": d.action.value,
                        "confidence_pct": float(d.confidence_pct) if d.confidence_pct is not None else None,
                        "running_count": d.running_count,
                        "true_count": float(d.true_count),
                        "bankroll_at_decision": float(d.bankroll_at_decision),
                        "optimal_reference_action": d.optimal_reference_action.value,
                        "agrees_with_optimal": d.agrees_with_optimal,
                        "state_snapshot": d.state_snapshot,
                        "model_response": {
                            "id": str(d.model_response.id),
                            "provider": d.model_response.provider.value,
                            "model_name": d.model_response.model_name,
                            "latency_ms": d.model_response.latency_ms,
                            "request_payload": d.model_response.request_payload,
                            "response_payload": d.model_response.response_payload,
                        } if d.model_response else None,
                    }
                    for d in sorted(h.decisions, key=lambda x: x.decision_number)
                ]

                result_data = None
                if h.result:
                    result_data = {
                        "id": str(h.result.id),
                        "result": h.result.result.value,
                        "player_value": h.result.player_value,
                        "dealer_value": h.result.dealer_value,
                        "payout_amount": float(h.result.payout_amount),
                        "net_amount": float(h.result.net_amount),
                    }

                hands.append({
                    "id": str(h.id),
                    "hand_number": h.hand_number,
                    "is_initial": h.is_initial,
                    "is_split": h.is_split,
                    "status": h.status.value,
                    "final_value": h.final_value,
                    "is_blackjack": h.is_blackjack,
                    "is_bust": h.is_bust,
                    "decisions": decisions,
                    "result": result_data,
                })

            bets = [
                {
                    "id": str(b.id),
                    "bet_type": b.bet_type.value,
                    "amount": float(b.amount),
                }
                for b in rp.bets
            ]

            txs = [
                {
                    "id": str(tx.id),
                    "transaction_type": tx.transaction_type.value,
                    "amount": float(tx.amount),
                    "balance_before": float(tx.balance_before),
                    "balance_after": float(tx.balance_after),
                    "created_at": tx.created_at.isoformat(),
                }
                for tx in sorted(rp.transactions, key=lambda t: t.created_at)
            ]

            players.append({
                "id": str(rp.id),
                "player_session_id": str(rp.player_session_id),
                "player_type": rp.player_session.player_type.value,
                "bankroll_before": float(rp.bankroll_before),
                "bankroll_after": float(rp.bankroll_after) if rp.bankroll_after is not None else None,
                "status": rp.status.value,
                "hands": hands,
                "bets": bets,
                "transactions": txs,
            })

        return {
            "round_id": str(round_obj.id),
            "round_number": round_obj.round_number,
            "status": round_obj.status.value,
            "dealer_final_value": round_obj.dealer_final_value,
            "dealer_blackjack": round_obj.dealer_blackjack,
            "dealer_bust": round_obj.dealer_bust,
            "started_at": round_obj.started_at.isoformat() if round_obj.started_at else None,
            "finished_at": round_obj.finished_at.isoformat() if round_obj.finished_at else None,
            "cards": cards,
            "players": players,
        }

    async def get_player_benchmark_summary(self, simulation_id: uuid.UUID) -> list[dict[str, Any]]:
        """Compute win rate, ROI, total wagers, and basic strategy agreement % per player."""
        stmt = (
            select(PlayerSession)
            .options(
                selectinload(PlayerSession.round_players)
                .selectinload(RoundPlayer.bets),
                selectinload(PlayerSession.round_players)
                .selectinload(RoundPlayer.hands)
                .selectinload(Hand.decisions),
                selectinload(PlayerSession.round_players)
                .selectinload(RoundPlayer.hands)
                .selectinload(Hand.result),
            )
            .where(PlayerSession.simulation_id == simulation_id)
        )
        res = await self.session.execute(stmt)
        sessions = res.scalars().all()

        summaries: list[dict[str, Any]] = []
        for ps in sessions:
            wins = 0
            losses = 0
            pushes = 0
            blackjacks = 0
            total_wagered = Decimal("0.00")
            total_decisions = 0
            optimal_decisions = 0
            rounds_played = len(ps.round_players)

            for rp in ps.round_players:
                for b in rp.bets:
                    total_wagered += b.amount

                for h in rp.hands:
                    if h.result:
                        res_val = h.result.result
                        if res_val == HandResultType.WIN:
                            wins += 1
                        elif res_val == HandResultType.LOSS or res_val == HandResultType.BUST:
                            losses += 1
                        elif res_val == HandResultType.PUSH:
                            pushes += 1
                        elif res_val == HandResultType.BLACKJACK:
                            wins += 1
                            blackjacks += 1
                        elif res_val == HandResultType.SURRENDER:
                            losses += 1

                    for d in h.decisions:
                        total_decisions += 1
                        if d.agrees_with_optimal:
                            optimal_decisions += 1

            net_profit = ps.current_bankroll - ps.initial_bankroll
            total_hands_resolved = wins + losses + pushes
            win_rate = round(float((Decimal(wins) / Decimal(total_hands_resolved)) * 100), 2) if total_hands_resolved > 0 else 0.0
            roi_pct = round(float((net_profit / total_wagered) * 100), 2) if total_wagered > Decimal("0.00") else 0.0
            agreement_pct = round(float((Decimal(optimal_decisions) / Decimal(total_decisions)) * 100), 2) if total_decisions > 0 else 100.0

            summaries.append({
                "player_session_id": str(ps.id),
                "player_type": ps.player_type.value,
                "initial_bankroll": float(ps.initial_bankroll),
                "final_bankroll": float(ps.current_bankroll),
                "net_profit": float(net_profit),
                "rounds_played": rounds_played,
                "wins": wins,
                "losses": losses,
                "pushes": pushes,
                "blackjacks": blackjacks,
                "win_rate": win_rate,
                "total_wagered": float(total_wagered),
                "roi_pct": roi_pct,
                "total_decisions": total_decisions,
                "optimal_decisions": optimal_decisions,
                "agreement_pct": agreement_pct,
            })

        return summaries
