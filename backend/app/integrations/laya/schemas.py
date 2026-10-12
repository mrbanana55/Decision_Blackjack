"""TypeSafe System One Pydantic v2 schemas and models for Laya integration."""

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
    """TypeSafe System One choice question."""

    model_config = ConfigDict(populate_by_name=True)

    type: Literal["choice"] = "choice"
    instructions: str = Field(
        ...,
        description="Text describing the judgment prompt the model should answer",
    )
    criteria: dict[str, str] = Field(
        ...,
        min_length=2,
        description="Dictionary mapping candidate keys to descriptive criteria",
    )


class SystemOneRequest(BaseModel):
    """Payload dispatched to POST /v1/systemone."""

    model_config = ConfigDict(populate_by_name=True)

    state: str = Field(
        ...,
        description="Observable state context for the model judgment",
    )
    questions: dict[str, ChoiceQuestion] = Field(
        ...,
        min_length=1,
        description="Dictionary of questions keyed by question identifier",
    )


class ChoiceAnswer(BaseModel):
    """Answer returned by Laya for a Choice question."""

    model_config = ConfigDict(populate_by_name=True)

    choice: str = Field(..., description="Selected option key from criteria")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    distribution: dict[str, float] = Field(
        default_factory=dict,
        description="Probability distribution across candidate options",
    )


class SystemOneResponse(BaseModel):
    """Parsed response returned from POST /v1/systemone."""

    model_config = ConfigDict(populate_by_name=True)

    answers: dict[str, ChoiceAnswer] = Field(
        default_factory=dict,
        description="Extracted answers keyed by question identifier",
    )
    meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Inference metadata (tokens, device, latency, model checkpoint)",
    )


class LayaHealthStatus(BaseModel):
    """Parsed response from GET /health."""

    model_config = ConfigDict(populate_by_name=True)

    status: str = Field(default="ok", description="Server status ('ok' when operational)")
    loaded: list[str] = Field(default_factory=list, description="Loaded model checkpoints")
    revisions: dict[str, str] = Field(default_factory=dict, description="Model revision git commits")
    device: str = Field(default="cpu", description="Execution device (e.g. mps, cuda, cpu)")
    device_is_preference: bool = False
    checkpoint_devices: dict[str, str] = Field(default_factory=dict)
    cpu_fallbacks: dict[str, Any] = Field(default_factory=dict)
