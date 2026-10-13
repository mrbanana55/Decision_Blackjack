"""REST endpoints for simulation lifecycle, configuration, and flow control."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import random
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.manager import simulation_manager
from app.api.schemas import (
    ControlCommandRequest,
    DecisionComparisonPayload,
    EntityDeviationStats,
    EntityMetricSummary,
    ErrorResponse,
    ExecutionMode,
    SimulationConfigRequest,
    SimulationDetailResponse,
    SimulationDeviationsResponse,
    SimulationListItem,
    SimulationListResponse,
    SimulationResponse,
    TableRulesConfig,
)
from app.persistence.database import get_db
from app.persistence.models import PlayerSession, Run, RunConfiguration, Simulation
from app.engine.card import Card
from app.engine.rules import TableRules
from app.engine.types import Action
from app.integrations.jev.agent import JevAgent
from app.integrations.jev.client import JevClient
from app.integrations.laya.agent import LayaAgent
from app.integrations.laya.client import LayaClient
from app.models.basic_strategy_player import BasicStrategyPlayer
from app.simulation.interfaces import DecisionProvider
from app.simulation.orchestrator import SimulationOrchestrator
from app.simulation.types import AgentDecision, DecisionContext, EntityType, SimulationConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/simulations", tags=["Simulations"])


class MockDecisionProvider:
    """Mock agent provider for offline testing and fast benchmarking."""

    def __init__(
        self,
        entity_type: EntityType,
        name: str,
        model_name: str,
        rules: TableRules,
    ) -> None:
        self.entity_type: EntityType = entity_type
        self.name: str = name
        self.model_name: str = model_name
        self.delegate: BasicStrategyPlayer = BasicStrategyPlayer(name=name, rules=rules)

    def observe_cards(self, cards: list[Card]) -> None:
        self.delegate.observe_cards(cards)

    def reset_count(self) -> None:
        self.delegate.reset_count()

    def get_bet(self, bankroll: float, min_bet: float) -> float:
        return self.delegate.get_bet(bankroll=bankroll, min_bet=min_bet)

    async def get_decision(self, context: DecisionContext) -> AgentDecision:
        decision = await self.delegate.get_decision(context)
        decision.metadata["model"] = self.model_name
        decision.metadata["mock"] = True
        return decision


async def _resolve_provider(
    entity_name: str,
    rules: TableRules,
    mock_mode: bool,
) -> DecisionProvider:
    """Instantiate requested decision entity provider with pre-flight health validation."""
    entity_lower = entity_name.lower()

    if entity_lower == "optimal":
        return BasicStrategyPlayer(rules=rules)

    if mock_mode:
        if entity_lower == "jev":
            return MockDecisionProvider(EntityType.JEV, "Jev", "jev-systemone-mock", rules)
        if entity_lower == "laya":
            return MockDecisionProvider(EntityType.LAYA, "Laya", "laya-local-mock", rules)

    # Real external service integration with pre-flight check
    if entity_lower == "jev":
        client = JevClient()
        try:
            health = await client.check_health()
            if health.status != "ok":
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Requested entity 'jev' is unavailable ({health.endpoint}). Configure TYPESAFE_API_KEY or enable mock_mode.",
                )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Pre-flight health check failed for 'jev': {exc}. Enable mock_mode for offline execution.",
            ) from exc
        finally:
            await client.close()
        return JevAgent()

    if entity_lower == "laya":
        client = LayaClient()
        try:
            health = await client.check_health()
            if health.status != "ok":
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Requested entity 'laya' is unavailable. Ensure local service is running or enable mock_mode.",
                )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Pre-flight health check failed for 'laya': {exc}. Enable mock_mode for offline execution.",
            ) from exc
        finally:
            await client.close()
        return LayaAgent()

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Unsupported entity: '{entity_name}'.",
    )


@router.post(
    "",
    response_model=SimulationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initialize and configure a new simulation run",
)
async def create_simulation(request: SimulationConfigRequest) -> SimulationResponse:
    """Validate table rules and configure an isolated multi-agent Blackjack experiment."""
    session_id = f"sim-{uuid.uuid4().hex[:8]}"
    run_id = str(uuid.uuid4())
    rules = request.table_rules.to_table_rules()
    seed = request.seed if request.seed is not None else random.randint(1, 10_000_000)

    # 1. Instantiate domain SimulationConfig
    sim_config = SimulationConfig(
        session_id=session_id,
        seed=seed,
        max_rounds=request.max_rounds,
        initial_bankroll=request.table_rules.initial_bankroll,
        table_rules=rules,
        stop_on_all_bankrupt=request.table_rules.stop_on_all_bankrupt,
    )

    # 2. Instantiate orchestrator
    orchestrator = SimulationOrchestrator(sim_config)

    # 3. Add isolated tables for each requested entity
    for entity_name in request.entities:
        provider = await _resolve_provider(
            entity_name=entity_name,
            rules=rules,
            mock_mode=request.mock_mode,
        )
        orchestrator.add_entity(
            entity_name,
            provider,
            initial_bankroll=request.table_rules.initial_bankroll,
        )

    # 4. Attempt to attach persistence listener if database is available
    try:
        from app.persistence.database import get_session_factory
        from app.persistence.listener import SimulationPersistenceListener

        factory = get_session_factory()
        listener = SimulationPersistenceListener(
            run_id=uuid.UUID(run_id),
            event_emitter=orchestrator.event_bus,
            session_factory=factory,
        )
        listener.attach()
    except Exception as exc:
        logger.debug("Database persistence listener not attached (running in standalone/mock mode): %s", exc)

    # 5. Register in SimulationManager
    record = simulation_manager.register_session(
        session_id=session_id,
        run_id=run_id,
        config=request,
        orchestrator=orchestrator,
    )

    # 6. For fast_batch mode, launch immediately; for visualized mode, status is INITIALIZING until connected or triggered
    if request.execution_mode == ExecutionMode.FAST_BATCH:
        simulation_manager.start_simulation(session_id)
        init_status = "RUNNING"
    else:
        init_status = "INITIALIZING"

    return SimulationResponse(
        session_id=session_id,
        run_id=run_id,
        status=init_status,
        execution_mode=request.execution_mode,
        current_round=0,
        max_rounds=request.max_rounds,
        num_simulations=request.num_simulations,
        entities=request.entities,
        websocket_url=f"/ws/simulations/{session_id}",
        created_at=record.created_at,
        table_rules=request.table_rules,
    )


@router.get(
    "",
    response_model=SimulationListResponse,
    summary="List past simulation runs with pagination",
)
async def list_simulations(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> SimulationListResponse:
    """Return paginated past simulation runs catalog."""
    offset = (page - 1) * page_size

    total_runs = 0
    db_runs: list[Run] = []
    try:
        total_stmt = select(func.count(Run.id))
        res_count = await db.execute(total_stmt)
        total_runs = res_count.scalar() or 0

        stmt = (
            select(Run)
            .options(
                selectinload(Run.configuration),
                selectinload(Run.simulations).selectinload(Simulation.player_sessions),
                selectinload(Run.simulations).selectinload(Simulation.rounds),
            )
            .order_by(Run.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        res_runs = await db.execute(stmt)
        db_runs = list(res_runs.scalars().all())
    except Exception as exc:
        logger.debug("Failed querying runs from database: %s", exc)

    items: list[SimulationListItem] = []
    seen_run_ids: set[str] = set()

    for run in db_runs:
        seen_run_ids.add(str(run.id))
        start_time = (
            run.started_at.isoformat()
            if run.started_at
            else (run.created_at.isoformat() if run.created_at else datetime.now(timezone.utc).isoformat())
        )
        end_time = run.finished_at.isoformat() if run.finished_at else None
        max_rounds = run.configuration.rounds_per_simulation if run.configuration else 0
        num_sims = run.configuration.simulations_count if run.configuration else len(run.simulations)
        seed = run.configuration.user_seed if (run.configuration and run.configuration.user_seed is not None) else 0
        total_rounds = sum(len(sim.rounds) for sim in run.simulations)

        entities: list[str] = []
        metrics: dict[str, EntityMetricSummary] = {}
        for sim in run.simulations:
            for ps in sim.player_sessions:
                ent_name = ps.player_type.value
                if ent_name not in entities:
                    entities.append(ent_name)
                net_profit = float(ps.current_bankroll - ps.initial_bankroll)
                rounds_played = len(sim.rounds)
                metrics[ent_name] = EntityMetricSummary(
                    entity_id=ent_name,
                    rounds_played=rounds_played,
                    net_profit=round(net_profit, 2),
                    current_bankroll=float(ps.current_bankroll),
                    win_rate=0.0,
                    optimality_rate=1.0,
                )

        items.append(
            SimulationListItem(
                run_id=str(run.id),
                session_id=f"sim-{run.id.hex[:8]}",
                status=run.status.value.upper(),
                start_time=start_time,
                end_time=end_time,
                total_rounds=total_rounds,
                max_rounds=max_rounds,
                num_simulations=num_sims,
                seed=seed,
                entities=entities,
                metrics=metrics,
            )
        )

    # Include any active in-memory sessions not yet committed to DB
    for rec in simulation_manager._sessions.values():
        if rec.run_id not in seen_run_ids:
            orch = rec.orchestrator
            orch_metrics: dict[str, EntityMetricSummary] = {}
            for tid, tbl in orch.tables.items():
                total_d = tbl.optimal_decisions + tbl.suboptimal_decisions
                opt_rate = (tbl.optimal_decisions / total_d) if total_d > 0 else 1.0
                win_rate = (tbl.wins / tbl.rounds_played) if tbl.rounds_played > 0 else 0.0
                orch_metrics[tid] = EntityMetricSummary(
                    entity_id=tid,
                    rounds_played=tbl.rounds_played,
                    net_profit=round(tbl.current_bankroll - tbl.starting_bankroll, 2),
                    current_bankroll=tbl.current_bankroll,
                    win_rate=round(win_rate, 4),
                    optimality_rate=round(opt_rate, 4),
                )
            items.insert(
                0,
                SimulationListItem(
                    run_id=rec.run_id,
                    session_id=rec.session_id,
                    status=orch.status.value.upper(),
                    start_time=rec.created_at,
                    end_time=None,
                    total_rounds=orch.current_round,
                    max_rounds=rec.config.max_rounds,
                    num_simulations=rec.config.num_simulations,
                    seed=orch.config.seed,
                    entities=rec.config.entities,
                    metrics=orch_metrics,
                ),
            )
            total_runs += 1

    return SimulationListResponse(
        items=items,
        total=total_runs,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{session_id}/start",
    summary="Explicitly trigger simulation execution",
)
async def start_simulation(session_id: str) -> dict[str, Any]:
    """Launch background execution loop for an initialized simulation session."""
    record = simulation_manager.get_session(session_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation session '{session_id}' not found.",
        )
    simulation_manager.start_simulation(session_id)
    return {
        "session_id": session_id,
        "status": "RUNNING",
    }


@router.get(
    "/{session_id}",
    response_model=SimulationDetailResponse,
    summary="Retrieve current status, metrics, and deviations for a simulation",
)
async def get_simulation(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> SimulationDetailResponse:
    """Retrieve runtime state and performance benchmarks for a simulation session."""
    record = simulation_manager.get_session(session_id)
    if record:
        orch = record.orchestrator
        metrics_summary: dict[str, EntityMetricSummary] = {}
        for tid, tbl in orch.tables.items():
            total_d = tbl.optimal_decisions + tbl.suboptimal_decisions
            opt_rate = (tbl.optimal_decisions / total_d) if total_d > 0 else 1.0
            win_rate = (tbl.wins / tbl.rounds_played) if tbl.rounds_played > 0 else 0.0
            metrics_summary[tid] = EntityMetricSummary(
                entity_id=tid,
                rounds_played=tbl.rounds_played,
                net_profit=round(tbl.current_bankroll - tbl.starting_bankroll, 2),
                current_bankroll=tbl.current_bankroll,
                win_rate=round(win_rate, 4),
                optimality_rate=round(opt_rate, 4),
            )

        return SimulationDetailResponse(
            run_id=record.run_id,
            session_id=record.session_id,
            status=orch.status.value.upper(),
            start_time=record.created_at,
            end_time=None,
            total_rounds=orch.current_round,
            max_rounds=record.config.max_rounds,
            num_simulations=record.config.num_simulations,
            seed=orch.config.seed,
            entities=record.config.entities,
            table_rules=record.config.table_rules,
            metrics=metrics_summary,
            deviations=record.deviations,
        )

    # Fallback to database lookup
    target_uuid: uuid.UUID | None = None
    try:
        target_uuid = uuid.UUID(session_id)
    except (ValueError, TypeError):
        pass

    run_obj: Run | None = None
    if target_uuid is not None:
        try:
            stmt = (
                select(Run)
                .options(
                    selectinload(Run.configuration),
                    selectinload(Run.simulations).selectinload(Simulation.player_sessions),
                    selectinload(Run.simulations).selectinload(Simulation.rounds),
                )
                .where(Run.id == target_uuid)
            )
            res = await db.execute(stmt)
            run_obj = res.scalar_one_or_none()
        except Exception as exc:
            logger.debug("Failed looking up run '%s' in database: %s", target_uuid, exc)

    if run_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation session '{session_id}' not found.",
        )

    start_time = (
        run_obj.started_at.isoformat()
        if run_obj.started_at
        else (run_obj.created_at.isoformat() if run_obj.created_at else datetime.now(timezone.utc).isoformat())
    )
    end_time = run_obj.finished_at.isoformat() if run_obj.finished_at else None
    max_rounds = run_obj.configuration.rounds_per_simulation if run_obj.configuration else 0
    num_sims = run_obj.configuration.simulations_count if run_obj.configuration else len(run_obj.simulations)
    seed = run_obj.configuration.user_seed if (run_obj.configuration and run_obj.configuration.user_seed is not None) else 0
    total_rounds = sum(len(sim.rounds) for sim in run_obj.simulations)

    entities: list[str] = []
    metrics: dict[str, EntityMetricSummary] = {}
    deviations: dict[str, EntityDeviationStats] = {}

    for sim in run_obj.simulations:
        for ps in sim.player_sessions:
            ent_name = ps.player_type.value
            if ent_name not in entities:
                entities.append(ent_name)
            net_profit = float(ps.current_bankroll - ps.initial_bankroll)
            rounds_played = len(sim.rounds)
            metrics[ent_name] = EntityMetricSummary(
                entity_id=ent_name,
                rounds_played=rounds_played,
                net_profit=round(net_profit, 2),
                current_bankroll=float(ps.current_bankroll),
                win_rate=0.0,
                optimality_rate=1.0,
            )
            deviations[ent_name] = EntityDeviationStats(entity_id=ent_name)

    if run_obj.configuration:
        cfg = run_obj.configuration
        table_rules = TableRulesConfig(
            soft_17_rule="S17" if cfg.soft_17_rule.name == "STAND" else "H17",
            blackjack_payout=float(cfg.blackjack_payout_ratio),
            hole_card_rule=cfg.hole_card_rule.name,
            insurance_allowed=cfg.insurance_enabled,
            surrender_rule=cfg.surrender_rule.name,
            double_after_split=cfg.das_enabled,
            max_split_hands=cfg.max_resplit + 1,
            resplit_aces=cfg.rsa_enabled,
            hit_split_aces=cfg.hit_split_aces,
            num_decks=cfg.number_of_decks,
            penetration=float(cfg.penetration),
            burn_cards_count=cfg.burn_cards,
            initial_bankroll=float(cfg.initial_bankroll),
            min_bet=float(cfg.minimum_bet),
            max_bet=float(cfg.maximum_bet),
        )
    else:
        table_rules = TableRulesConfig()

    return SimulationDetailResponse(
        run_id=str(run_obj.id),
        session_id=session_id,
        status=run_obj.status.value.upper(),
        start_time=start_time,
        end_time=end_time,
        total_rounds=total_rounds,
        max_rounds=max_rounds,
        num_simulations=num_sims,
        seed=seed,
        entities=entities,
        table_rules=table_rules,
        metrics=metrics,
        deviations=deviations,
    )


@router.get(
    "/{session_id}/deviations",
    response_model=SimulationDeviationsResponse,
    summary="Retrieve real-time strategy deviation statistics for all active players",
)
async def get_simulation_deviations(session_id: str) -> SimulationDeviationsResponse:
    """Query live Basic Strategy discrepancy statistics broken down by category and bet spread."""
    record = simulation_manager.get_session(session_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation session '{session_id}' not found.",
        )

    return SimulationDeviationsResponse(
        session_id=record.session_id,
        current_round=record.orchestrator.current_round,
        entities=record.deviations,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )


@router.post(
    "/{session_id}/control",
    summary="Send flow control command via REST fallback",
)
async def control_simulation(
    session_id: str,
    body: ControlCommandRequest,
) -> dict[str, Any]:
    """Apply interactive flow control command (pause, resume, step, set_speed, stop, retry)."""
    record = simulation_manager.get_session(session_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation session '{session_id}' not found.",
        )

    cmd = body.command.lower()
    try:
        if cmd == "pause":
            await simulation_manager.pause(session_id)
        elif cmd == "resume":
            await simulation_manager.resume(session_id)
        elif cmd == "step":
            await simulation_manager.step(session_id, level=body.level or "round")
        elif cmd == "set_speed":
            if body.delay_ms is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="delay_ms is required for set_speed")
            await simulation_manager.set_speed(session_id, body.delay_ms)
        elif cmd == "stop":
            await simulation_manager.stop(session_id)
        elif cmd == "retry":
            await simulation_manager.retry(session_id, entity_id=body.entity_id)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown command '{body.command}'")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {
        "session_id": session_id,
        "status": record.orchestrator.status.value.upper(),
        "command_applied": cmd,
    }
