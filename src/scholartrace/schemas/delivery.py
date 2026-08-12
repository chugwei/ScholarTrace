"""Evidence-bound contracts for M12 delivery artifacts and cards."""

from datetime import datetime
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scholartrace.schemas.research import NonBlankText, RequiredTextList
from scholartrace.schemas.runner import validate_relative_path

EvidenceClass = Literal["synthetic_fixture", "offline_test", "staging", "real_field"]
DeliveryStatus = Literal["draft", "verified"]
MetricVerificationStatus = Literal["verified", "unverified", "not_available"]


class DeliveryEvidence(BaseModel):
    """Describe whether a card is synthetic, offline, staging, or field evidence."""

    model_config = ConfigDict(extra="forbid")

    evidence_class: EvidenceClass
    source_ref: NonBlankText
    validation_record_ref: NonBlankText | None = None

    @model_validator(mode="after")
    def require_field_record(self) -> "DeliveryEvidence":
        if self.evidence_class == "real_field" and self.validation_record_ref is None:
            raise ValueError("real_field evidence requires a validation_record_ref")
        return self


class ModelMetric(BaseModel):
    """One metric in a Model Card with an explicit evidence boundary."""

    model_config = ConfigDict(extra="forbid")

    name: NonBlankText
    value: float | None = None
    unit: NonBlankText | None = None
    split: NonBlankText | None = None
    verification_status: MetricVerificationStatus = "not_available"
    evidence: DeliveryEvidence


class ModelCard(BaseModel):
    """Minimum Model Card required before a model enters a delivery manifest."""

    model_config = ConfigDict(extra="forbid")

    model_card_id: NonBlankText
    model_name: NonBlankText
    model_version: NonBlankText
    task: NonBlankText
    intended_use: NonBlankText
    out_of_scope_uses: RequiredTextList
    training_data_ref: NonBlankText
    evaluation_data_ref: NonBlankText
    metrics: list[ModelMetric] = Field(default_factory=list)
    limitations: RequiredTextList
    ethical_considerations: RequiredTextList
    model_artifact_relpath: NonBlankText | None = None
    model_artifact_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    evidence: DeliveryEvidence

    @model_validator(mode="after")
    def validate_artifact_pair(self) -> "ModelCard":
        if (self.model_artifact_relpath is None) != (self.model_artifact_sha256 is None):
            raise ValueError("model artifact path and SHA-256 must be supplied together")
        if self.model_artifact_relpath is not None:
            self.model_artifact_relpath = validate_relative_path(
                self.model_artifact_relpath, field_name="model artifact path"
            )
        return self


class DataCard(BaseModel):
    """Minimum Data Card required for a delivery package."""

    model_config = ConfigDict(extra="forbid")

    data_card_id: NonBlankText
    dataset_name: NonBlankText
    dataset_version: NonBlankText
    purpose: NonBlankText
    source_description: NonBlankText
    license_or_access: NonBlankText
    collection_protocol_ref: NonBlankText
    preprocessing: RequiredTextList
    split_strategy: NonBlankText
    known_limitations: RequiredTextList
    privacy_review: NonBlankText
    evidence: DeliveryEvidence


class DeliveryArtifact(BaseModel):
    """One file in a delivery tree with its expected hash and size."""

    model_config = ConfigDict(extra="forbid")

    relative_path: NonBlankText
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)
    media_type: NonBlankText
    required: bool = True

    @model_validator(mode="after")
    def validate_path(self) -> "DeliveryArtifact":
        self.relative_path = validate_relative_path(
            self.relative_path, field_name="delivery artifact path"
        )
        return self


class DeliveryManifest(BaseModel):
    """Reproducible package index linking cards, files, and source revision."""

    model_config = ConfigDict(extra="forbid")

    delivery_id: NonBlankText
    product_name: NonBlankText = "研迹 ScholarTrace"
    product_version: NonBlankText
    source_revision: str = Field(pattern=r"^[0-9a-f]{7,64}$")
    generated_at: datetime
    entrypoint: NonBlankText
    install_command: NonBlankText
    model_card: ModelCard
    data_card: DataCard
    artifacts: list[DeliveryArtifact] = Field(min_length=1)
    evidence: DeliveryEvidence
    status: DeliveryStatus = "draft"

    @model_validator(mode="after")
    def validate_manifest(self) -> "DeliveryManifest":
        paths = [artifact.relative_path for artifact in self.artifacts]
        if len(paths) != len(set(paths)):
            raise ValueError("delivery artifact paths must be unique")
        if self.status == "verified" and self.evidence.evidence_class == "synthetic_fixture":
            raise ValueError("synthetic_fixture delivery cannot be marked verified")
        return self


class DeliveryVerificationEntry(BaseModel):
    """Result for one expected delivery artifact."""

    model_config = ConfigDict(extra="forbid")

    relative_path: NonBlankText
    status: Literal["passed", "missing", "hash_mismatch", "size_mismatch"]
    expected_sha256: str
    actual_sha256: str | None = None
    expected_size_bytes: int
    actual_size_bytes: int | None = None


class DeliveryVerificationReport(BaseModel):
    """Deterministic verification result for a delivery tree."""

    model_config = ConfigDict(extra="forbid")

    delivery_id: NonBlankText
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    entries: list[DeliveryVerificationEntry]
    passed: bool


class HealthProbeResult(BaseModel):
    """One HTTP health probe with explicit failure details."""

    model_config = ConfigDict(extra="forbid")

    endpoint: NonBlankText
    status_code: int | None = None
    ok: bool
    payload: dict[str, object] = Field(default_factory=dict)
    error: NonBlankText | None = None
    checked_at: datetime


class ReleasePointer(BaseModel):
    """A delivery version that can be activated or rolled back to."""

    model_config = ConfigDict(extra="forbid")

    release_id: NonBlankText
    delivery_id: NonBlankText
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    root_relpath: NonBlankText
    activated_at: datetime


class ReleaseState(BaseModel):
    """Atomic active/previous release pointers for local Staging rollback."""

    model_config = ConfigDict(extra="forbid")

    active: ReleasePointer | None = None
    previous: ReleasePointer | None = None
    history: list[ReleasePointer] = Field(default_factory=list)


class RollbackOutcome(BaseModel):
    """Record whether a release was rolled back during or after validation."""

    model_config = ConfigDict(extra="forbid")

    attempted: bool
    active_release_id: NonBlankText | None = None
    notes: NonBlankText | None = None

    @model_validator(mode="after")
    def require_active_when_attempted(self) -> "RollbackOutcome":
        if self.attempted and self.active_release_id is None:
            raise ValueError("attempted rollback must record the resulting active_release_id")
        return self


class FieldEnvironmentContext(BaseModel):
    """On-site environment context that only real field records may carry.

    The fields mirror the M12.5 plan: data source, device, environment,
    ethics/privacy, operator, time, code/data/model versions and rollback
    outcome. Ethics approval and the named operator are mandatory because a
    real field claim without them is unverifiable.
    """

    model_config = ConfigDict(extra="forbid")

    site_name: NonBlankText
    location_description: NonBlankText
    device_description: NonBlankText
    capture_conditions: NonBlankText
    operator_name: NonBlankText
    privacy_review: NonBlankText
    ethics_approval_ref: NonBlankText


class FieldProvenance(BaseModel):
    """Code, data and model versioning plus the delivery manifest binding."""

    model_config = ConfigDict(extra="forbid")

    code_version: NonBlankText
    data_version: NonBlankText
    model_version: NonBlankText
    manifest_delivery_id: NonBlankText
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class FieldValidationRecord(BaseModel):
    """One validation record whose tier is bound to its evidence class.

    Synthetic, offline and staging records are forbidden from carrying field
    environment context so they cannot masquerade as real field evidence.
    Real field records must carry full environment and provenance context.
    """

    model_config = ConfigDict(extra="forbid")

    record_id: NonBlankText
    evidence: DeliveryEvidence
    conducted_at: datetime
    summary: NonBlankText
    environment: FieldEnvironmentContext | None = None
    provenance: FieldProvenance | None = None
    rollback_outcome: RollbackOutcome | None = None

    @model_validator(mode="after")
    def gate_field_context_by_evidence_class(self) -> "FieldValidationRecord":
        if self.evidence.evidence_class != "real_field":
            if self.environment is not None:
                raise ValueError("field environment is only permitted for real_field records")
            return self
        if self.environment is None or self.provenance is None:
            raise ValueError("real_field record requires full environment and provenance context")
        return self


class FieldValidationSummary(BaseModel):
    """Aggregate validation records by evidence class without tier inflation.

    A real_field conclusion may only be drawn from real_field records. Lower
    tiers stay separable so synthetic/offline/staging results can never be
    packaged as a real field conclusion.
    """

    model_config = ConfigDict(extra="forbid")

    summary_id: NonBlankText
    product_version: NonBlankText
    generated_at: datetime
    conclusion_class: EvidenceClass
    records: list[FieldValidationRecord] = Field(default_factory=list)
    notes: NonBlankText | None = None

    @model_validator(mode="after")
    def guard_conclusion_class(self) -> "FieldValidationSummary":
        record_classes = {record.evidence.evidence_class for record in self.records}
        if self.conclusion_class == "real_field" and record_classes != {"real_field"}:
            raise ValueError("real_field conclusion requires real_field records only")
        return self

    @property
    def record_count_by_class(self) -> dict[str, int]:
        counts: dict[str, int] = {tier: 0 for tier in get_args(EvidenceClass)}
        for record in self.records:
            key = record.evidence.evidence_class
            counts[key] = counts.get(key, 0) + 1
        return counts
