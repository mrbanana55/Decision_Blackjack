# Phase 1 Data Model: Jev Decision Agent Integration

**Feature Branch**: `006-jev-agent-integration`  
**Date**: 2026-10-12  
**Status**: Completed  

---

## 1. Domain & Integration Models (`backend/app/integrations/jev/schemas.py`)

### 1.1 Question & Primitive Models

#### `QuestionType` (str, Enum)
Supported TypeSafe question primitives:
- `CHOICE`: `"choice"`
- `SCORE`: `"score"`
- `NOUL`: `"noul"`

#### `HandSituationType` (str, Enum)
Categorized tactical blackjack situations:
- `INITIAL_PAIR_SPLIT`: `"initial_pair_split"`
- `INITIAL_STANDARD`: `"initial_standard"`
- `MULTI_CARD_DRAW`: `"multi_card_draw"`
- `INSURANCE_OFFER`: `"insurance_offer"`
- `ROUND_BETTING`: `"round_betting"`

#### `ChoiceQuestion` (BaseModel)
Single TypeSafe System One Choice question definition:
- `type`: `Literal["choice"] = "choice"`
- `instructions` (str): Text prompt describing the judgment for the model.
- `criteria` (dict[str, str]): Map of option keys to descriptive rubric criteria (min length: 2).

---

### 1.2 Request & Response Payloads

#### `SystemOneRequest` (BaseModel)
Payload dispatched to `POST /v1/systemone`:
- `state` (str): Formatted observable table context.
- `model` (str): Target model alias (default: `"jev-latest"`).
- `questions` (dict[str, ChoiceQuestion]): Named questions map (min length: 1).

#### `ChoiceAnswer` (BaseModel)
Answer extracted for a Choice question:
- `choice` (str): Highest-probability option key selected from criteria.
- `confidence` (float): Confidence score in range `[0.0, 1.0]`.
- `probabilities` (dict[str, float]): Probability distribution across candidate options.

#### `UsageInfo` (BaseModel)
Token usage metadata from TypeSafe API response:
- `input_tokens` (int): Number of prompt/context tokens consumed.
- `output_tokens` (int): Number of completion/decision tokens consumed.

#### `SystemOneResponse` (BaseModel)
Parsed response returned from TypeSafe System One:
- `model` (str): Evaluating model revision identifier.
- `answers` (dict[str, ChoiceAnswer]): Extracted answers keyed by question identifier.
- `usage` (UsageInfo | None): Token usage statistics.
- `meta` (dict[str, Any]): Additional client-attached telemetry (e.g., `latency_ms`, HTTP status).

---

### 1.3 Health & Diagnostic Models

#### `JevHealthStatus` (BaseModel)
Parsed response from `/health/jev`:
- `status` (str): `"ok"` or `"unavailable"`.
- `provider` (str): `"typesafe"`.
- `model` (str): Configured model alias (e.g., `"jev-latest"`).
- `endpoint` (str): Effective API endpoint URL.
- `has_api_key` (bool): Whether a valid non-empty API key is configured.
- `details` (dict[str, Any]): Additional connection telemetry.

---

### 1.4 Configuration Model (`backend/app/integrations/jev/config.py`)

#### `JevConfig` (BaseModel)
Runtime configuration loaded from `.env`:
- `api_key` (str): Sourced from `TYPESAFE_API_KEY`.
- `api_url` (str): Sourced from `TYPESAFE_API_URL` (default: `https://api.typesafe.ai/v1/systemone`).
- `model` (str): Sourced from `TYPESAFE_MODEL` (default: `jev-latest`).
- `timeout_seconds` (float): Sourced from `TYPESAFE_TIMEOUT_SECONDS` (default: `15.0`).
- `connect_timeout_seconds` (float): Sourced from `TYPESAFE_CONNECT_TIMEOUT_SECONDS` (default: `3.0`).
- `max_retries` (int): Sourced from `TYPESAFE_MAX_RETRIES` (default: `3`).
- `backoff_factor` (float): Sourced from `TYPESAFE_BACKOFF_FACTOR` (default: `1.0`).

---

## 2. Entity Mapping & Orchestrator Integration

### 2.1 Action Mapping

Criteria option keys in `ChoiceQuestion` map directly to domain actions:

| Criteria Key | Domain `Action` | Active Phase / Condition |
| :--- | :--- | :--- |
| `hit` | `Action.HIT` | While player hand is not busted or standing |
| `stand` | `Action.STAND` | Conclude turn on active hand |
| `double` | `Action.DOUBLE` | Initial 2-card hand when bankroll $\ge$ bet |
| `split` | `Action.SPLIT` | Paired 2-card hand when bankroll $\ge$ bet |
| `surrender` | `Action.SURRENDER` | Initial 2-card hand when late surrender enabled |
| `accept` | `True` (Insurance) | When dealer exposed card is Ace |
| `decline` | `False` (Insurance) | When dealer exposed card is Ace |
| `1x`, `2x`, `4x`, `8x` | Bet Multiplier | Pre-deal round wager sizing |

### 2.2 `AgentDecision` Synthesis

When Jev returns a decision, `JevAgent` constructs an `AgentDecision`:
```python
AgentDecision(
    action=mapped_action,
    confidence=answer.confidence,
    latency_ms=elapsed_ms,
    reasoning=f"Jev System One chose {mapped_action.name} (confidence {answer.confidence:.2f})",
    metadata={
        "provider": "jev",
        "model": response.model,
        "input_tokens": usage.input_tokens if usage else None,
        "output_tokens": usage.output_tokens if usage else None,
        "probabilities": answer.probabilities,
        "situation": situation.value,
        "endpoint": config.api_url,
    }
)
```

---

## 3. Persistence Schema Alignment

Jev telemetry seamlessly populates existing PostgreSQL tables:
- `decisions`:
  - `decision_number`: Turn sequence index
  - `action`: `PlayerAction`
  - `confidence_pct`: Extracted from `confidence * 100`
  - `optimal_reference_action`: Computed by `DecisionComparator`
  - `agrees_with_optimal`: Boolean agreement flag
- `model_responses`:
  - `provider`: `ModelProvider.SYSTEM_ONE`
  - `model_name`: Sourced from response (`jev-latest` or specific revision)
  - `request_payload`: Full JSON request sent to `/v1/systemone`
  - `response_payload`: Full JSON response received
  - `latency_ms`: Measured round-trip HTTP duration
