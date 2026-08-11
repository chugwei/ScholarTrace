"""Input/output contracts for the M12 inference boundary."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scholartrace.schemas.delivery import DeliveryEvidence
from scholartrace.schemas.research import NonBlankText
from scholartrace.schemas.runner import validate_relative_path

InferenceStatus = Literal["predicted", "rejected", "unavailable"]


class InferenceRequest(BaseModel):
    """A content-addressed request against one delivery-tree input file."""

    model_config = ConfigDict(extra="forbid")

    request_id: NonBlankText
    input_relpath: NonBlankText
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_version: NonBlankText | None = None

    @model_validator(mode="after")
    def validate_path(self) -> "InferenceRequest":
        validate_relative_path(self.input_relpath, field_name="inference input path")
        return self


class Prediction(BaseModel):
    """One prediction with an explicit evidence classification."""

    model_config = ConfigDict(extra="forbid")

    label: NonBlankText
    score: float = Field(ge=0, le=1)
    evidence: DeliveryEvidence


class InferenceResponse(BaseModel):
    """Content-addressed prediction response and its warnings."""

    model_config = ConfigDict(extra="forbid")

    request_id: NonBlankText
    delivery_id: NonBlankText
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_version: NonBlankText
    status: InferenceStatus
    predictions: list[Prediction]
    warnings: list[NonBlankText] = Field(default_factory=list)
    created_at: datetime
