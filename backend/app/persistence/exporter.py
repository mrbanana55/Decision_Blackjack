"""Run Archival Exporter serializing completed simulations to JSON artifacts.

Formats the complete 15-entity relational hierarchy into /data/runs/[timestamp]/run_data.json.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    Decision,
    Hand,
    Round,
    RoundPlayer,
    Run,
    Shoe,
    Simulation,
)


class EntityJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder handling UUIDs, Decimals, datetimes, and Enums."""

    def default(self, o: Any) -> Any:
        if isinstance(o, uuid.UUID):
            return str(o)
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, Enum):
            return o.value
        return super().default(o)


class RunExporter:
    """Exports a completed simulation run to structured file records."""

    def __init__(self, session: AsyncSession, base_dir: Path | str = "/app/data/runs") -> None:
        """Initialize RunExporter.

        Args:
            session: Active database session.
            base_dir: Root directory for run exports.
        """
        self.session = session
        self.base_dir = Path(base_dir)

    async def export_run_to_json(self, run_id: uuid.UUID) -> Path:
        """Serialize run, configurations, simulations, rounds, and metrics to JSON artifact.

        Args:
            run_id: UUID of the run to export.

        Returns:
            Path to the written run_data.json artifact.
        """
        stmt = (
            select(Run)
            .options(
                selectinload(Run.configuration),
                selectinload(Run.simulations)
                .selectinload(Simulation.player_sessions),
                selectinload(Run.simulations)
                .selectinload(Simulation.shoes)
                .selectinload(Shoe.player_states),
                selectinload(Run.simulations)
                .selectinload(Simulation.rounds)
                .selectinload(Round.card_events),
                selectinload(Run.simulations)
                .selectinload(Simulation.rounds)
                .selectinload(Round.round_players)
                .selectinload(RoundPlayer.bets),
                selectinload(Run.simulations)
                .selectinload(Simulation.rounds)
                .selectinload(Round.round_players)
                .selectinload(RoundPlayer.transactions),
                selectinload(Run.simulations)
                .selectinload(Simulation.rounds)
                .selectinload(Round.round_players)
                .selectinload(RoundPlayer.hands)
                .selectinload(Hand.bets),
                selectinload(Run.simulations)
                .selectinload(Simulation.rounds)
                .selectinload(Round.round_players)
                .selectinload(RoundPlayer.hands)
                .selectinload(Hand.result),
                selectinload(Run.simulations)
                .selectinload(Simulation.rounds)
                .selectinload(Round.round_players)
                .selectinload(RoundPlayer.hands)
                .selectinload(Hand.card_events),
                selectinload(Run.simulations)
                .selectinload(Simulation.rounds)
                .selectinload(Round.round_players)
                .selectinload(RoundPlayer.hands)
                .selectinload(Hand.decisions)
                .selectinload(Decision.model_response),
            )
            .where(Run.id == run_id)
        )

        res = await self.session.execute(stmt)
        run = res.scalar_one_or_none()
        if run is None:
            raise ValueError(f"Run '{run_id}' not found in database.")

        payload = self._build_run_dict(run)

        # Directory formatting: [base_dir]/[timestamp]
        ts_str = run.created_at.strftime("%Y%m%d_%H%M%S") if run.created_at else datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        target_dir = self.base_dir / ts_str
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / "run_data.json"

        with open(target_file, "w", encoding="utf-8") as f:  # noqa: ASYNC230
            json.dump(payload, f, cls=EntityJSONEncoder, indent=2)

        # Update run data directory record
        run.data_directory = str(target_dir)
        await self.session.commit()

        return target_file

    def _build_run_dict(self, run: Run) -> dict[str, Any]:
        """Construct full relational dictionary for run."""
        cfg_dict: dict[str, Any] = {}
        if run.configuration:
            cfg = run.configuration
            cfg_dict = {
                "id": str(cfg.id),
                "soft_17_rule": cfg.soft_17_rule.value,
                "blackjack_payout_ratio": float(cfg.blackjack_payout_ratio),
                "split_aces_blackjack_rule": cfg.split_aces_blackjack_rule.value,
                "hole_card_rule": cfg.hole_card_rule.value,
                "insurance_enabled": cfg.insurance_enabled,
                "insurance_payout_ratio": float(cfg.insurance_payout_ratio),
                "surrender_rule": cfg.surrender_rule.value,
                "das_enabled": cfg.das_enabled,
                "max_resplit": cfg.max_resplit,
                "rsa_enabled": cfg.rsa_enabled,
                "hit_split_aces": cfg.hit_split_aces,
                "charlie_rule": cfg.charlie_rule.value,
                "number_of_decks": cfg.number_of_decks,
                "penetration": float(cfg.penetration),
                "burn_cards": cfg.burn_cards,
                "initial_bankroll": float(cfg.initial_bankroll),
                "minimum_bet": float(cfg.minimum_bet),
                "maximum_bet": float(cfg.maximum_bet),
                "rounds_per_simulation": cfg.rounds_per_simulation,
                "rounds_indefinite": cfg.rounds_indefinite,
                "simulations_count": cfg.simulations_count,
                "simulations_indefinite": cfg.simulations_indefinite,
                "user_seed": cfg.user_seed,
                "optimal_bet_spread": cfg.optimal_bet_spread,
            }

        sims_list: list[dict[str, Any]] = []
        for sim in run.simulations:
            player_sessions = [
                {
                    "id": str(ps.id),
                    "player_type": ps.player_type.value,
                    "initial_bankroll": float(ps.initial_bankroll),
                    "current_bankroll": float(ps.current_bankroll),
                    "status": ps.status.value,
                }
                for ps in sim.player_sessions
            ]

            shoes = [
                {
                    "id": str(sh.id),
                    "shoe_number": sh.shoe_number,
                    "seed": sh.seed,
                    "card_order": sh.card_order,
                    "total_cards": sh.total_cards,
                    "burn_cards": sh.burn_cards,
                    "penetration": float(sh.penetration),
                }
                for sh in sim.shoes
            ]

            rounds = []
            for r in sim.rounds:
                card_events = [
                    {
                        "id": str(ce.id),
                        "sequence_number": ce.sequence_number,
                        "recipient": ce.recipient.value,
                        "card": ce.card,
                        "shoe_position": ce.shoe_position,
                    }
                    for ce in r.card_events
                ]

                round_players = []
                for rp in r.round_players:
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
                            for d in h.decisions
                        ]

                        hand_res = None
                        if h.result:
                            hand_res = {
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
                            "result": hand_res,
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
                        }
                        for tx in rp.transactions
                    ]

                    round_players.append({
                        "id": str(rp.id),
                        "player_session_id": str(rp.player_session_id),
                        "bankroll_before": float(rp.bankroll_before),
                        "bankroll_after": float(rp.bankroll_after) if rp.bankroll_after is not None else None,
                        "status": rp.status.value,
                        "hands": hands,
                        "bets": bets,
                        "transactions": txs,
                    })

                rounds.append({
                    "id": str(r.id),
                    "round_number": r.round_number,
                    "status": r.status.value,
                    "dealer_final_value": r.dealer_final_value,
                    "dealer_blackjack": r.dealer_blackjack,
                    "dealer_bust": r.dealer_bust,
                    "card_events": card_events,
                    "round_players": round_players,
                })

            sims_list.append({
                "id": str(sim.id),
                "simulation_number": sim.simulation_number,
                "seed": sim.seed,
                "status": sim.status.value,
                "initial_bankroll": float(sim.initial_bankroll),
                "final_bankroll": float(sim.final_bankroll) if sim.final_bankroll is not None else None,
                "player_sessions": player_sessions,
                "shoes": shoes,
                "rounds": rounds,
            })

        return {
            "run_id": str(run.id),
            "status": run.status.value,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "error_message": run.error_message,
            "data_directory": run.data_directory,
            "configuration": cfg_dict,
            "simulations": sims_list,
        }
