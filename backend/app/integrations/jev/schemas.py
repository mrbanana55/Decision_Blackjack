"""TypeSafe System One Pydantic v2 schemas and models for Jev integration."""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class QuestionType(str, Enum):
    """Supported TypeSafe question primitives."""

    CHOICE = "choice"
    SCORE = "score"
    NOUL = "noul"


class HandSituationType(str, Enum):
    """Categorized tactical situations for situational schema generation."""

    INITIAL_PAIR_SPLIT = "initial_pair_split"
    INITIAL_STANDARD = "initial_standard"
    MULTI_CARD_DRAW = "multi_card_draw"
    INSURANCE_OFFER = "insurance_offer"
    ROUND_BETTING = "round_betting"


class ChoiceQuestion(BaseModel):
    """TypeSafe System One choice question definition."""

    model_config = ConfigDict(populate_by_name=True)

    type: Literal["choice"] = "choice"
    instructions: str = Field(
        ...,
        description="Text describing the judgment prompt the model should answer",
    )
    criteria: dict[str, str] = Field(
        ...,
        min_length=2,
        description="Dictionary mapping candidate keys to descriptive rubric criteria",
    )


class SystemOneRequest(BaseModel):
    """Payload dispatched to TypeSafe POST /v1/systemone."""

    model_config = ConfigDict(populate_by_name=True)

    state: str = Field(
        ...,
        description="Observable state context for the model judgment",
    )
    model: str = Field(
        default="jev-latest",
        description="Target model identifier (e.g. jev-latest)",
    )
    questions: dict[str, ChoiceQuestion] = Field(
        ...,
        min_length=1,
        description="Dictionary of questions keyed by question identifier",
    )


class ChoiceAnswer(BaseModel):
    """Answer extracted for a Choice question from TypeSafe System One."""

    model_config = ConfigDict(populate_by_name=True)

    choice: str = Field(..., description="Selected option key from criteria")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    probabilities: dict[str, float] = Field(
        default_factory=dict,
        description="Probability distribution across candidate options",
    )

    @property
    def distribution(self) -> dict[str, float]:
        """Convenience property for compatibility with distribution callers."""
        return self.probabilities


class UsageInfo(BaseModel):
    """Token usage metadata returned by TypeSafe API."""

    model_config = ConfigDict(populate_by_name=True)

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)


class SystemOneResponse(BaseModel):
    """Parsed response returned from TypeSafe System One API."""

    model_config = ConfigDict(populate_by_name=True)

    model: str = Field(default="jev-latest", description="Evaluating model revision")
    answers: dict[str, ChoiceAnswer] = Field(
        default_factory=dict,
        description="Extracted answers keyed by question identifier",
    )
    usage: UsageInfo | None = Field(
        default=None,
        description="Token usage statistics",
    )
    meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Client-attached metadata (latency_ms, http_status, endpoint)",
    )


class JevHealthStatus(BaseModel):
    """Status model for Jev health probes."""

    model_config = ConfigDict(populate_by_name=True)

    status: str = Field(default="ok", description="Status ('ok' or 'unavailable')")
    provider: str = Field(default="typesafe", description="Provider identifier")
    model: str = Field(default="jev-latest", description="Configured model identifier")
    endpoint: str = Field(default="", description="Target API endpoint")
    has_api_key: bool = Field(default=True, description="Whether API key is present")
    details: dict[str, Any] = Field(default_factory=dict)
