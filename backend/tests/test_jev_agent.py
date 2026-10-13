"""Unit tests for JevAgent DecisionProvider implementation."""

from unittest.mock import AsyncMock

import pytest

from app.engine.card import Card, Rank, Suit
from app.engine.types import Action
from app.integrations.jev.agent import JevAgent
from app.integrations.jev.schemas import ChoiceAnswer, SystemOneResponse, UsageInfo
from app.simulation.interfaces import AgentFaultError
from app.simulation.types import AgentDecision, DecisionContext, EntityType


@pytest.fixture
def mock_context() -> DecisionContext:
    return DecisionContext(
        session_id="test-sim-jev-agent",
        round_number=1,
        hand_index=0,
        player_cards=[Card(Suit.SPADES, Rank.TEN), Card(Suit.HEARTS, Rank.SIX)],
        player_total=16,
        is_soft=False,
        dealer_upcard=Card(Suit.CLUBS, Rank.SEVEN),
        legal_actions=[Action.HIT, Action.STAND, Action.DOUBLE],
        true_count=0.0,
    )


@pytest.mark.asyncio
async def test_jev_agent_properties():
    """Verify name and entity_type properties on JevAgent."""
    agent = JevAgent()
    assert agent.name == "Jev"
    assert agent.entity_type == EntityType.JEV


@pytest.mark.asyncio
async def test_jev_agent_get_decision_hit(mock_context):
    """Verify JevAgent maps 'hit' choice response to Action.HIT with confidence and telemetry."""
    mock_client = AsyncMock()
    mock_client.send_systemone.return_value = SystemOneResponse(
        model="jev-latest",
        answers={
            "action": ChoiceAnswer(
                choice="hit",
                confidence=0.92,
                probabilities={"hit": 0.92, "stand": 0.08},
            )
        },
        usage=UsageInfo(input_tokens=150, output_tokens=20),
        meta={"latency_ms": 45.0},
    )

    agent = JevAgent(client=mock_client)
    decision: AgentDecision = await agent.get_decision(mock_context)

    assert decision.action == Action.HIT
    assert decision.confidence == 0.92
    assert decision.latency_ms > 0
    assert decision.metadata["provider"] == "typesafe"
    assert decision.metadata["model"] == "jev-latest"
    assert decision.metadata["input_tokens"] == 150
    assert decision.metadata["output_tokens"] == 20
    assert decision.metadata["probabilities"]["hit"] == 0.92
    assert mock_client.send_systemone.await_count == 1


@pytest.mark.asyncio
async def test_jev_agent_get_decision_all_actions():
    """Verify mapping across all possible blackjack actions."""
    mock_client = AsyncMock()
    agent = JevAgent(client=mock_client)

    action_map = {
        "hit": Action.HIT,
        "stand": Action.STAND,
        "double": Action.DOUBLE,
        "split": Action.SPLIT,
        "surrender": Action.SURRENDER,
    }

    all_actions_context = DecisionContext(
        session_id="test-sim-jev-agent",
        round_number=1,
        hand_index=0,
        player_cards=[Card(Suit.SPADES, Rank.EIGHT), Card(Suit.HEARTS, Rank.EIGHT)],
        player_total=16,
        is_soft=False,
        dealer_upcard=Card(Suit.CLUBS, Rank.SEVEN),
        legal_actions=list(action_map.values()),
        true_count=0.0,
    )

    for choice_str, expected_action in action_map.items():
        mock_client.send_systemone.return_value = SystemOneResponse(
            model="jev-latest",
            answers={"action": ChoiceAnswer(choice=choice_str, confidence=0.88)},
            meta={"latency_ms": 15.0},
        )
        decision = await agent.get_decision(all_actions_context)
        assert decision.action == expected_action


@pytest.mark.asyncio
async def test_jev_agent_illegal_action_fallback(mock_context):
    """Verify JevAgent safely falls back to legal Stand/Hit when model returns illegal action."""
    mock_client = AsyncMock()
    # Model chooses split, but split is NOT in mock_context.legal_actions (which has HIT, STAND, DOUBLE)
    mock_client.send_systemone.return_value = SystemOneResponse(
        model="jev-latest",
        answers={"action": ChoiceAnswer(choice="split", confidence=0.99)},
        meta={"latency_ms": 10.0},
    )

    agent = JevAgent(client=mock_client)
    decision = await agent.get_decision(mock_context)
    # Should safely fall back to Action.STAND
    assert decision.action == Action.STAND


@pytest.mark.asyncio
async def test_jev_agent_client_fault_propagation(mock_context):
    """Verify AgentFaultError from JevClient propagates to trigger orchestrator pause."""
    mock_client = AsyncMock()
    mock_client.send_systemone.side_effect = AgentFaultError("TypeSafe API rate limit exceeded")

    agent = JevAgent(client=mock_client)
    with pytest.raises(AgentFaultError, match="TypeSafe API rate limit exceeded"):
        await agent.get_decision(mock_context)


@pytest.mark.asyncio
async def test_jev_agent_get_bet():
    """Verify JevAgent.get_bet parses discrete multiplier choices and handles bankroll boundaries."""
    mock_client = AsyncMock()
    agent = JevAgent(client=mock_client)

    # 4x bet multiplier
    mock_client.send_systemone.return_value = SystemOneResponse(
        model="jev-latest",
        answers={"bet_sizing": ChoiceAnswer(choice="4x", confidence=0.95)},
    )
    bet = await agent.get_bet(bankroll=1000.0, min_bet=50.0, true_count=2.0)
    assert bet == 200.0  # 4 * 50

    # 8x capped by bankroll ($300 available, 8 * 50 = $400)
    mock_client.send_systemone.return_value = SystemOneResponse(
        model="jev-latest",
        answers={"bet_sizing": ChoiceAnswer(choice="8x", confidence=0.95)},
    )
    bet = await agent.get_bet(bankroll=300.0, min_bet=50.0, true_count=3.5)
    assert bet == 300.0

    # Fallback to min_bet on exception
    mock_client.send_systemone.side_effect = AgentFaultError("Network fault")
    bet = await agent.get_bet(bankroll=1000.0, min_bet=50.0)
    assert bet == 50.0


@pytest.mark.asyncio
async def test_jev_agent_get_insurance():
    """Verify JevAgent.get_insurance returns boolean decision from accept/decline choices."""
    mock_client = AsyncMock()
    agent = JevAgent(client=mock_client)
    context = DecisionContext(
        session_id="test-ins",
        round_number=1,
        hand_index=0,
        player_cards=[Card(Suit.SPADES, Rank.TEN), Card(Suit.HEARTS, Rank.TEN)],
        player_total=20,
        is_soft=False,
        dealer_upcard=Card(Suit.CLUBS, Rank.ACE),
        legal_actions=[],
        can_insure=True,
    )

    # Accept
    mock_client.send_systemone.return_value = SystemOneResponse(
        model="jev-latest",
        answers={"insurance": ChoiceAnswer(choice="accept", confidence=0.90)},
    )
    assert await agent.get_insurance(context, insurance_cost=25.0) is True

    # Decline
    mock_client.send_systemone.return_value = SystemOneResponse(
        model="jev-latest",
        answers={"insurance": ChoiceAnswer(choice="decline", confidence=0.90)},
    )
    assert await agent.get_insurance(context, insurance_cost=25.0) is False

    # Failure defaults to False
    mock_client.send_systemone.side_effect = AgentFaultError("Error")
    assert await agent.get_insurance(context, insurance_cost=25.0) is False
