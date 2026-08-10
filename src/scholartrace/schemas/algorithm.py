"""Evidence-linked contracts for algorithm design and innovation candidates."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from scholartrace.schemas.research import NonBlankText

AlgorithmStatus = Literal["draft", "approved", "rejected", "superseded"]
PriorArtStatus = Literal["draft", "approved", "rejected", "superseded"]
InnovationReviewStatus = Literal[
    "draft",
    "under_review",
    "approved_for_experiment",
    "rejected",
    "withdrawn",
]
NoveltyStatus = Literal[
    "unverified",
    "partially_supported",
    "conflicting",
    "not_novel",
]
Sha256Text = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
TextList = list[NonBlankText]


class AlgorithmComponent(BaseModel):
    """One independently reviewable component of an algorithm design."""

    model_config = ConfigDict(extra="forbid")

    component_id: NonBlankText
    name: NonBlankText
    role: NonBlankText
    inputs: TextList = Field(min_length=1)
    outputs: TextList = Field(min_length=1)
    rationale: NonBlankText
    implementation_notes: list[NonBlankText] = Field(default_factory=list)


class AlgorithmSpec(BaseModel):
    """Versioned algorithm design tied to an approved research design."""

    model_config = ConfigDict(extra="forbid")

    algorithm_id: NonBlankText
    project_id: NonBlankText
    version: int = Field(ge=1)
    status: AlgorithmStatus = "draft"
    title: NonBlankText
    problem: NonBlankText
    task_type: NonBlankText
    inputs: TextList = Field(min_length=1)
    outputs: TextList = Field(min_length=1)
    components: list[AlgorithmComponent] = Field(min_length=1)
    training_objective: NonBlankText
    inference_strategy: NonBlankText
    evaluation_protocol: NonBlankText
    pipeline_id: NonBlankText
    protocol_id: NonBlankText
    evidence_card_ids: list[NonBlankText] = Field(min_length=1)
    assumptions: list[NonBlankText] = Field(default_factory=list)
    risks: list[NonBlankText] = Field(default_factory=list)
    content_sha256: Sha256Text | None = None
    parent_algorithm_id: NonBlankText | None = None
    created_by: NonBlankText
    decision_reason: str | None = None
    approved_by: NonBlankText | None = None
    approved_at: datetime | None = None
    created_at: datetime

    @model_validator(mode="after")
    def validate_component_ids(self) -> "AlgorithmSpec":
        component_ids = [component.component_id for component in self.components]
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("algorithm component_id values must be unique")
        return self


class PriorArtEntry(BaseModel):
    """One prior-work row backed by project evidence cards."""

    model_config = ConfigDict(extra="forbid")

    prior_art_entry_id: NonBlankText
    title: NonBlankText
    evidence_card_ids: list[NonBlankText] = Field(min_length=1)
    method_summary: NonBlankText
    reported_strengths: TextList = Field(min_length=1)
    reported_limitations: TextList = Field(min_length=1)
    applicability_notes: NonBlankText


class PriorArtMap(BaseModel):
    """Versioned map from an algorithm design to traceable prior work."""

    model_config = ConfigDict(extra="forbid")

    map_id: NonBlankText
    project_id: NonBlankText
    algorithm_id: NonBlankText
    version: int = Field(ge=1)
    status: PriorArtStatus = "draft"
    entries: list[PriorArtEntry] = Field(min_length=1)
    unresolved_search_gaps: list[NonBlankText] = Field(default_factory=list)
    content_sha256: Sha256Text | None = None
    parent_map_id: NonBlankText | None = None
    created_by: NonBlankText
    decision_reason: str | None = None
    approved_by: NonBlankText | None = None
    approved_at: datetime | None = None
    created_at: datetime

    @model_validator(mode="after")
    def validate_entry_ids(self) -> "PriorArtMap":
        entry_ids = [entry.prior_art_entry_id for entry in self.entries]
        if len(entry_ids) != len(set(entry_ids)):
            raise ValueError("prior-art entry IDs must be unique")
        return self


class MethodDifference(BaseModel):
    """One explicit, reviewable difference between prior art and a candidate."""

    model_config = ConfigDict(extra="forbid")

    dimension: NonBlankText
    prior_art_entry_id: NonBlankText
    prior_art_approach: NonBlankText
    proposed_approach: NonBlankText
    expected_effect: NonBlankText


class InnovationCandidate(BaseModel):
    """A falsifiable candidate; this model never asserts proven novelty."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: NonBlankText
    project_id: NonBlankText
    algorithm_id: NonBlankText
    prior_art_map_id: NonBlankText
    version: int = Field(ge=1)
    status: InnovationReviewStatus = "draft"
    title: NonBlankText
    problem: NonBlankText
    prior_art_entry_ids: list[NonBlankText] = Field(min_length=1)
    prior_art_evidence_ids: list[NonBlankText] = Field(min_length=1)
    differences: list[MethodDifference] = Field(min_length=1)
    identified_gap: NonBlankText
    proposed_change: NonBlankText
    expected_mechanism: NonBlankText
    expected_benefit: NonBlankText
    novelty_status: NoveltyStatus = "unverified"
    falsification_experiment: NonBlankText
    required_baselines: TextList = Field(min_length=1)
    required_ablations: TextList = Field(min_length=1)
    risks: list[NonBlankText] = Field(default_factory=list)
    content_sha256: Sha256Text | None = None
    parent_candidate_id: NonBlankText | None = None
    created_by: NonBlankText
    decision_reason: str | None = None
    approved_by: NonBlankText | None = None
    approved_at: datetime | None = None
    created_at: datetime


class InnovationFinding(BaseModel):
    """A deterministic reason a candidate cannot pass the experiment gate."""

    model_config = ConfigDict(extra="forbid")

    code: NonBlankText
    severity: Literal["error", "warning", "info"]
    message: NonBlankText


class InnovationValidationReport(BaseModel):
    """Machine-checkable candidate gate output."""

    model_config = ConfigDict(extra="forbid")

    passed: bool
    findings: list[InnovationFinding] = Field(default_factory=list)


class InnovationCandidateRanking(BaseModel):
    """Deterministic completeness ranking, not a claim of scientific novelty."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: NonBlankText
    score: float = Field(ge=0, le=1)
    rationale: list[NonBlankText] = Field(min_length=1)


class CandidateExperimentPlan(BaseModel):
    """A proposed falsification plan, not an executed experiment result."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: NonBlankText
    hypothesis: NonBlankText
    falsification_experiment: NonBlankText
    required_baselines: TextList = Field(min_length=1)
    required_ablations: TextList = Field(min_length=1)
    evaluation_requirements: TextList = Field(min_length=1)
    status: Literal["proposed"] = "proposed"
