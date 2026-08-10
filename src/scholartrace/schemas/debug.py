"""Evidence-bound debugging and safe repair contracts."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from scholartrace.schemas.research import NonBlankText

FailureCategory = Literal[
    "unknown",
    "data",
    "configuration",
    "environment",
    "resource",
    "convergence",
    "evaluation",
    "code",
    "access",
    "reproducibility",
]
DebugCaseStatus = Literal[
    "captured",
    "diagnosed",
    "fix_proposed",
    "approved",
    "regression_failed",
    "regression_passed",
    "resolved",
    "rejected",
]
DiagnosticStatus = Literal["pass", "fail", "unknown"]
RegressionStatus = Literal["passed", "failed"]


class EvidenceRef(BaseModel):
    """A pointer to observed evidence, never generated scientific prose."""

    model_config = ConfigDict(extra="forbid")

    source: NonBlankText
    detail: NonBlankText


class DiagnosticHypothesis(BaseModel):
    """A ranked, falsifiable explanation for a failed run."""

    model_config = ConfigDict(extra="forbid")

    hypothesis_id: NonBlankText
    category: FailureCategory
    statement: NonBlankText
    priority: int = Field(ge=1)
    evidence: list[EvidenceRef] = Field(default_factory=list)


class DiagnosticFinding(BaseModel):
    """Result of a read-only diagnostic check."""

    model_config = ConfigDict(extra="forbid")

    finding_id: NonBlankText
    status: DiagnosticStatus
    check: NonBlankText
    detail: NonBlankText
    evidence: list[EvidenceRef] = Field(default_factory=list)


class RepairFileChange(BaseModel):
    """Text-only change guarded by an optional expected source hash."""

    model_config = ConfigDict(extra="forbid")

    relative_path: NonBlankText
    expected_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    replacement_text: str


class RepairProposal(BaseModel):
    """Minimal fix requiring human approval before application."""

    model_config = ConfigDict(extra="forbid")

    fix_id: NonBlankText
    case_id: NonBlankText
    summary: NonBlankText
    rationale: NonBlankText
    changes: list[RepairFileChange] = Field(min_length=1)
    regression_command: list[NonBlankText] = Field(min_length=1)
    rollback_plan: NonBlankText
    created_by: NonBlankText
    created_at: datetime


class RegressionResult(BaseModel):
    """Observed result of a regression command in the repair workspace."""

    model_config = ConfigDict(extra="forbid")

    status: RegressionStatus
    command: list[NonBlankText] = Field(min_length=1)
    exit_code: int
    output_excerpt: str = Field(default="", max_length=20_000)
    checked_at: datetime


class DebugCase(BaseModel):
    """Versioned evidence chain from failure capture to resolution."""

    model_config = ConfigDict(extra="forbid")

    case_id: NonBlankText
    project_id: NonBlankText
    execution_id: NonBlankText
    status: DebugCaseStatus = "captured"
    category: FailureCategory
    observed_error: NonBlankText
    expected_behavior: NonBlankText
    actual_behavior: NonBlankText
    staging_relpath: NonBlankText | None = None
    log_relpath: NonBlankText | None = None
    environment: dict[str, NonBlankText] = Field(default_factory=dict)
    hypotheses: list[DiagnosticHypothesis] = Field(default_factory=list)
    findings: list[DiagnosticFinding] = Field(default_factory=list)
    proposal: RepairProposal | None = None
    approved_by: NonBlankText | None = None
    approval_reason: NonBlankText | None = None
    regression: RegressionResult | None = None
    resolution: NonBlankText | None = None
    created_at: datetime
    updated_at: datetime
