"""Structured contracts for reproducible pipeline and data-collection designs."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from scholartrace.schemas.research import NonBlankText

DesignStatus = Literal["draft", "approved", "rejected", "superseded"]
FindingSeverity = Literal["error", "warning", "info"]
Sha256Text = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
TextList = list[NonBlankText]


class PipelineStage(BaseModel):
    """One named, ordered stage in a research pipeline."""

    model_config = ConfigDict(extra="forbid")

    stage_id: NonBlankText
    name: NonBlankText
    purpose: NonBlankText
    inputs: TextList = Field(min_length=1)
    outputs: TextList = Field(min_length=1)
    tools: TextList = Field(default_factory=list)


class PipelineSpec(BaseModel):
    """Versioned, reviewable design for data, training, evaluation and delivery."""

    model_config = ConfigDict(extra="forbid")

    pipeline_id: NonBlankText
    project_id: NonBlankText
    version: int = Field(ge=1)
    status: DesignStatus = "draft"
    title: NonBlankText
    objective: NonBlankText
    stages: list[PipelineStage] = Field(min_length=1)
    evaluation_protocol: NonBlankText
    artifact_outputs: TextList = Field(min_length=1)
    assumptions: TextList = Field(default_factory=list)
    risks: TextList = Field(default_factory=list)
    content_sha256: Sha256Text | None = None
    parent_pipeline_id: NonBlankText | None = None
    created_by: NonBlankText
    decision_reason: str | None = None
    approved_by: NonBlankText | None = None
    approved_at: datetime | None = None
    created_at: datetime

    @model_validator(mode="after")
    def validate_stage_ids(self) -> "PipelineSpec":
        stage_ids = [stage.stage_id for stage in self.stages]
        if len(stage_ids) != len(set(stage_ids)):
            raise ValueError("pipeline stage_id values must be unique")
        return self


class CaptureField(BaseModel):
    """One required or optional field captured during data collection."""

    model_config = ConfigDict(extra="forbid")

    field_name: NonBlankText
    description: NonBlankText
    required: bool = True


class DataCollectionProtocol(BaseModel):
    """Versioned protocol for sampling, capture, annotation and leakage control."""

    model_config = ConfigDict(extra="forbid")

    protocol_id: NonBlankText
    project_id: NonBlankText
    version: int = Field(ge=1)
    status: DesignStatus = "draft"
    title: NonBlankText
    target_population: NonBlankText
    sampling_strategy: NonBlankText
    inclusion_criteria: TextList = Field(min_length=1)
    exclusion_criteria: TextList = Field(default_factory=list)
    capture_fields: list[CaptureField] = Field(min_length=1)
    annotation_policy: NonBlankText
    split_strategy: NonBlankText
    leakage_controls: TextList = Field(min_length=1)
    consent_and_privacy: NonBlankText
    content_sha256: Sha256Text | None = None
    parent_protocol_id: NonBlankText | None = None
    created_by: NonBlankText
    decision_reason: str | None = None
    approved_by: NonBlankText | None = None
    approved_at: datetime | None = None
    created_at: datetime

    @model_validator(mode="after")
    def validate_capture_fields(self) -> "DataCollectionProtocol":
        names = [field.field_name for field in self.capture_fields]
        if len(names) != len(set(names)):
            raise ValueError("capture field_name values must be unique")
        included = set(self.inclusion_criteria)
        excluded = included.intersection(self.exclusion_criteria)
        if excluded:
            raise ValueError("inclusion and exclusion criteria must not overlap")
        return self


class DesignFinding(BaseModel):
    """One deterministic quality or leakage finding."""

    model_config = ConfigDict(extra="forbid")

    code: NonBlankText
    severity: FindingSeverity
    message: NonBlankText
    path: NonBlankText


class DesignValidationReport(BaseModel):
    """Validation output that must be clean before a design pair is approved."""

    model_config = ConfigDict(extra="forbid")

    passed: bool
    findings: list[DesignFinding] = Field(default_factory=list)


class PipelineVersionComparison(BaseModel):
    """Auditable summary of changes between two pipeline versions."""

    model_config = ConfigDict(extra="forbid")

    project_id: NonBlankText
    from_pipeline_id: NonBlankText
    to_pipeline_id: NonBlankText
    from_version: int = Field(ge=1)
    to_version: int = Field(ge=1)
    changed_fields: list[NonBlankText] = Field(default_factory=list)
    added_stage_ids: list[NonBlankText] = Field(default_factory=list)
    removed_stage_ids: list[NonBlankText] = Field(default_factory=list)
