"""Evidence-bound contracts for M12 delivery artifacts and cards."""

from datetime import datetime
from typing import Literal

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
            validate_relative_path(self.model_artifact_relpath, field_name="model artifact path")
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
        validate_relative_path(self.relative_path, field_name="delivery artifact path")
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
