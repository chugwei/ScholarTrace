"""Contracts for reproducible experiment plans and matrices."""

import math
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from scholartrace.schemas.research import NonBlankText

ExperimentPlanStatus = Literal["draft", "frozen", "rejected", "superseded"]
MatrixMethodKind = Literal["baseline", "proposed", "ablation"]
RunImportStatus = Literal["imported", "incomplete", "validated", "failed"]
MetricSource = Literal["training_log", "imported_report", "independent_recompute"]
MetricVerificationStatus = Literal["unverifiable", "verified", "rejected"]
Sha256Text = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
TextList = list[NonBlankText]


class ExperimentMatrixEntry(BaseModel):
    """One reproducible row in a frozen experiment matrix."""

    model_config = ConfigDict(extra="forbid")

    matrix_entry_id: NonBlankText
    name: NonBlankText
    method_kind: MatrixMethodKind
    method_ref: NonBlankText
    dataset_version: NonBlankText
    config_ref: NonBlankText
    seeds: list[int] = Field(min_length=1)
    repeats: int = Field(ge=1)
    metrics: TextList = Field(min_length=1)

    @model_validator(mode="after")
    def validate_seeds(self) -> "ExperimentMatrixEntry":
        if len(self.seeds) != len(set(self.seeds)):
            raise ValueError("matrix seeds must be unique")
        return self


class ExperimentPlan(BaseModel):
    """Versioned plan whose frozen form is the only formal run input."""

    model_config = ConfigDict(extra="forbid")

    plan_id: NonBlankText
    project_id: NonBlankText
    algorithm_id: NonBlankText
    candidate_id: NonBlankText | None = None
    version: int = Field(ge=1)
    status: ExperimentPlanStatus = "draft"
    objective: NonBlankText
    hypotheses: TextList = Field(min_length=1)
    datasets: TextList = Field(min_length=1)
    baselines: TextList = Field(min_length=1)
    proposed_methods: TextList = Field(min_length=1)
    independent_variables: TextList = Field(min_length=1)
    controlled_variables: TextList = Field(min_length=1)
    metrics: TextList = Field(min_length=1)
    statistical_tests: list[NonBlankText] = Field(default_factory=list)
    seeds: list[int] = Field(min_length=1)
    repeats: int = Field(ge=1)
    ablations: TextList = Field(min_length=1)
    resource_budget: dict[str, object]
    stopping_criteria: TextList = Field(min_length=1)
    expected_artifacts: TextList = Field(min_length=1)
    failure_and_fallback_plan: TextList = Field(min_length=1)
    matrix: list[ExperimentMatrixEntry] = Field(min_length=1)
    data_version: NonBlankText
    code_sha256: Sha256Text
    environment_lock: NonBlankText
    config_refs: TextList = Field(min_length=1)
    content_sha256: Sha256Text | None = None
    parent_plan_id: NonBlankText | None = None
    created_by: NonBlankText
    decision_reason: str | None = None
    approved_by: NonBlankText | None = None
    approved_at: datetime | None = None
    created_at: datetime

    @model_validator(mode="after")
    def validate_matrix(self) -> "ExperimentPlan":
        matrix_ids = [entry.matrix_entry_id for entry in self.matrix]
        if len(matrix_ids) != len(set(matrix_ids)):
            raise ValueError("experiment matrix_entry_id values must be unique")
        if len(self.seeds) != len(set(self.seeds)):
            raise ValueError("experiment plan seeds must be unique")
        return self


class RunManifest(BaseModel):
    """Imported run metadata; missing provenance makes it incomplete."""

    model_config = ConfigDict(extra="forbid")

    run_id: NonBlankText
    project_id: NonBlankText
    plan_id: NonBlankText
    matrix_entry_id: NonBlankText
    status: RunImportStatus = "imported"
    code_sha256: Sha256Text | None = None
    data_version: NonBlankText | None = None
    config_ref: NonBlankText | None = None
    environment_lock: NonBlankText | None = None
    seed: int | None = None
    checkpoint_sha256: Sha256Text | None = None
    log_relpath: NonBlankText | None = None
    config_relpath: NonBlankText | None = None
    weights_relpath: NonBlankText | None = None
    metrics_relpath: NonBlankText | None = None
    artifact_relpaths: list[NonBlankText] = Field(default_factory=list)
    missing_requirements: list[NonBlankText] = Field(default_factory=list)
    imported_at: datetime

    @model_validator(mode="after")
    def validate_relative_paths(self) -> "RunManifest":
        paths = [
            self.log_relpath,
            self.config_relpath,
            self.weights_relpath,
            self.metrics_relpath,
            *self.artifact_relpaths,
        ]
        for path in paths:
            if path is None:
                continue
            normalized = path.replace("\\", "/")
            if normalized.startswith("/") or ":" in normalized[:3] or ".." in normalized.split("/"):
                raise ValueError(
                    "run artifact paths must be relative and stay within the artifact root"
                )
        return self


class MetricResult(BaseModel):
    """A metric with an explicit provenance and verification state."""

    model_config = ConfigDict(extra="forbid")

    metric_result_id: NonBlankText
    project_id: NonBlankText
    run_id: NonBlankText
    name: NonBlankText
    split: NonBlankText
    value: float
    source: MetricSource
    verification_status: MetricVerificationStatus = "unverifiable"
    is_final: bool = False
    data_version: NonBlankText | None = None
    evaluation_script_sha256: Sha256Text | None = None
    created_at: datetime

    @model_validator(mode="after")
    def validate_provenance(self) -> "MetricResult":
        if not math.isfinite(self.value):
            raise ValueError("metric value must be finite")
        if self.source in {"training_log", "imported_report"} and (
            self.verification_status != "unverifiable" or self.is_final
        ):
            raise ValueError(
                "reported metrics cannot be marked final without independent recomputation"
            )
        if self.verification_status == "verified":
            if self.source != "independent_recompute" or not self.is_final:
                raise ValueError("verified metrics must come from an independent recomputation")
            if self.data_version is None or self.evaluation_script_sha256 is None:
                raise ValueError(
                    "verified metrics require data_version and evaluation script provenance"
                )
        return self
