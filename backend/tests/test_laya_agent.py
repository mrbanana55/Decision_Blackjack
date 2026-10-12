"""Unit tests for LayaAgent DecisionProvider implementation."""

from unittest.mock import AsyncMock

import pytest

from app.engine.card import Card, Rank, Suit
from app.engine.types import Action
from app.integrations.laya.agent import LayaAgent
from app.integrations.laya.schemas import ChoiceAnswer, SystemOneResponse
from app.simulation.interfaces import AgentFaultError
from app.simulation.types import AgentDecision, DecisionContext, EntityType


@pytest.fixture
def mock_context() -> DecisionContext:
    return DecisionContext(
        session_id="test-sim-agent",
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
async def test_laya_agent_properties():
    """Verify name and entity_type properties on LayaAgent."""
    agent = LayaAgent()
    assert agent.name == "Laya"
    assert agent.entity_type == EntityType.LAYA


@pytest.mark.asyncio
async def test_laya_agent_get_decision_hit(mock_context):
    """Verify LayaAgent maps 'hit' choice response to Action.HIT with confidence and telemetry."""
    mock_client = AsyncMock()
    mock_client.send_systemone.return_value = SystemOneResponse(
        answers={
            "action": ChoiceAnswer(
                choice="hit",
                confidence=0.94,
                distribution={"hit": 0.94, "stand": 0.06},
            )
        },
        meta={"device": "mps", "latency_ms": 22.5, "model": "typed-decisions"},
    )

    agent = LayaAgent(client=mock_client)
    decision: AgentDecision = await agent.get_decision(mock_context)

    assert decision.action == Action.HIT
    assert decision.confidence == 0.94
    assert decision.latency_ms > 0
    assert decision.metadata["device"] == "mps"
    assert decision.metadata["provider"] == "laya"
    assert mock_client.send_systemone.await_count == 1


@pytest.mark.asyncio
async def test_laya_agent_get_decision_all_actions():
    """Verify mapping across all possible blackjack actions."""
    mock_client = AsyncMock()
    agent = LayaAgent(client=mock_client)

    action_map = {
        "hit": Action.HIT,
        "stand": Action.STAND,
        "double": Action.DOUBLE,
        "split": Action.SPLIT,
        "surrender": Action.SURRENDER,
    }

    all_actions_context = DecisionContext(
        session_id="test-sim-agent",
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
            answers={"action": ChoiceAnswer(choice=choice_str, confidence=0.88)},
            meta={"latency_ms": 15.0},
        )
        decision = await agent.get_decision(all_actions_context)
        assert decision.action == expected_action


@pytest.mark.asyncio
async def test_laya_agent_client_fault_propagation(mock_context):
    """Verify that network/client exceptions raise AgentFaultError."""
    mock_client = AsyncMock()
    mock_client.send_systemone.side_effect = AgentFaultError("Connection refused to host")

    agent = LayaAgent(client=mock_client)
    with pytest.raises(AgentFaultError, match="Connection refused"):
        await agent.get_decision(mock_context)


@pytest.mark.asyncio
async def test_laya_agent_get_bet():
    """Verify LayaAgent.get_bet parses discrete multiplier choices and handles fallback."""
    mock_client = AsyncMock()
    agent = LayaAgent(client=mock_client)

    # 4x multiplier on $50 min_bet
    mock_client.send_systemone.return_value = SystemOneResponse(
        answers={"bet_sizing": ChoiceAnswer(choice="4x", confidence=0.85)}
    )
    bet = await agent.get_bet(bankroll=1000.0, min_bet=50.0, true_count=2.0)
    assert bet == 200.0

    # 8x multiplier on $25 min_bet
    mock_client.send_systemone.return_value = SystemOneResponse(
        answers={"bet_sizing": ChoiceAnswer(choice="8x", confidence=0.90)}
    )
    bet = await agent.get_bet(bankroll=1000.0, min_bet=25.0, true_count=4.0)
    assert bet == 200.0

    # Bankroll cap constraint: 8x ($400) when bankroll is $150
    mock_client.send_systemone.return_value = SystemOneResponse(
        answers={"bet_sizing": ChoiceAnswer(choice="8x", confidence=0.90)}
    )
    bet = await agent.get_bet(bankroll=150.0, min_bet=50.0)
    assert bet == 150.0

    # Failure fallback: defaults to min_bet
    mock_client.send_systemone.side_effect = RuntimeError("Network error")
    bet = await agent.get_bet(bankroll=1000.0, min_bet=50.0)
    assert bet == 50.0


@pytest.mark.asyncio
async def test_laya_agent_get_insurance(mock_context):
    """Verify LayaAgent.get_insurance returns boolean decision from accept/decline choices."""
    mock_client = AsyncMock()
    agent = LayaAgent(client=mock_client)

    # Accept
    mock_client.send_systemone.return_value = SystemOneResponse(
        answers={"insurance": ChoiceAnswer(choice="accept", confidence=0.82)}
    )
    accepted = await agent.get_insurance(mock_context, insurance_cost=25.0)
    assert accepted is True

    # Decline
    mock_client.send_systemone.return_value = SystemOneResponse(
        answers={"insurance": ChoiceAnswer(choice="decline", confidence=0.91)}
    )
    accepted = await agent.get_insurance(mock_context, insurance_cost=25.0)
    assert accepted is False

    # Failure fallback: decline
    mock_client.send_systemone.side_effect = RuntimeError("Timeout")
    accepted = await agent.get_insurance(mock_context, insurance_cost=25.0)
    assert accepted is False
