"""M12.5 field-validation evidence-tiering contracts.

These tests enforce that synthetic, offline, and staging records cannot be
dressed up as real field evidence, and that real field records must carry the
full provenance, ethics, and environment context the plan requires.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from scholartrace.schemas.delivery import (
    DeliveryEvidence,
    FieldEnvironmentContext,
    FieldProvenance,
    FieldValidationRecord,
    FieldValidationSummary,
    RollbackOutcome,
)

_NOW = datetime(2026, 8, 11, 9, 30, tzinfo=UTC)


def _synthetic_evidence() -> DeliveryEvidence:
    return DeliveryEvidence(
        evidence_class="synthetic_fixture",
        source_ref="tests/fixtures/projects/lychee-pest-detection.json",
    )


def _staging_evidence() -> DeliveryEvidence:
    return DeliveryEvidence(
        evidence_class="staging",
        source_ref="staging://compose/inference-smoke",
        validation_record_ref="docs/verification/m12-compose.md",
    )


def _real_field_evidence() -> DeliveryEvidence:
    return DeliveryEvidence(
        evidence_class="real_field",
        source_ref="field://orchard-A/lychee-pest-2026-08",
        validation_record_ref="docs/field/orchard-A-2026-08.md",
    )


def _environment() -> FieldEnvironmentContext:
    return FieldEnvironmentContext(
        site_name="Orchard A",
        location_description="lychee orchard, Guangdong, China",
        device_description="USB camera, Raspberry Pi 4",
        capture_conditions="daylight, 14:00 local",
        operator_name="on-site collaborator (named in private record)",
        privacy_review="faces and licence plates redacted; consent form on file",
        ethics_approval_ref="IRB-2026-ORCHARD-A",
    )


def _provenance() -> FieldProvenance:
    return FieldProvenance(
        code_version="4922b05",
        data_version="field-orchard-A-2026-08",
        model_version="fixture-1",
        manifest_delivery_id="delivery-lychee-field",
        manifest_sha256="a" * 64,
    )


def test_synthetic_record_cannot_carry_field_environment() -> None:
    with pytest.raises(ValidationError, match="field environment is only permitted"):
        FieldValidationRecord(
            record_id="field-001",
            evidence=_synthetic_evidence(),
            conducted_at=_NOW,
            summary="synthetic run",
            environment=_environment(),
            provenance=_provenance(),
        )


def test_staging_record_cannot_carry_field_environment() -> None:
    with pytest.raises(ValidationError, match="field environment is only permitted"):
        FieldValidationRecord(
            record_id="staging-001",
            evidence=_staging_evidence(),
            conducted_at=_NOW,
            summary="staging run",
            environment=_environment(),
            provenance=_provenance(),
        )


def test_real_field_record_requires_full_environment_and_provenance() -> None:
    base = dict(
        record_id="field-001",
        evidence=_real_field_evidence(),
        conducted_at=_NOW,
        summary="on-site evaluation",
    )
    with pytest.raises(ValidationError, match="real_field record requires"):
        FieldValidationRecord(**base, provenance=_provenance())
    with pytest.raises(ValidationError, match="real_field record requires"):
        FieldValidationRecord(**base, environment=_environment())
    record = FieldValidationRecord(
        **base,
        environment=_environment(),
        provenance=_provenance(),
        rollback_outcome=RollbackOutcome(
            attempted=False, active_release_id="release-field-2026-08", notes="no rollback needed"
        ),
    )
    assert record.evidence.evidence_class == "real_field"


def test_real_field_environment_requires_ethics_and_operator() -> None:
    with pytest.raises(ValidationError, match="ethics_approval_ref"):
        FieldEnvironmentContext(
            site_name="Orchard A",
            location_description="lychee orchard",
            device_description="camera",
            capture_conditions="daylight",
            operator_name="collaborator",
            privacy_review="redacted",
            ethics_approval_ref="",
        )
    with pytest.raises(ValidationError, match="operator_name"):
        FieldEnvironmentContext(
            site_name="Orchard A",
            location_description="lychee orchard",
            device_description="camera",
            capture_conditions="daylight",
            operator_name="",
            privacy_review="redacted",
            ethics_approval_ref="IRB-2026",
        )


def test_summary_rejects_lower_tier_records_for_real_field_conclusion() -> None:
    synthetic_record = FieldValidationRecord(
        record_id="rec-synthetic",
        evidence=_synthetic_evidence(),
        conducted_at=_NOW,
        summary="synthetic run",
    )
    with pytest.raises(ValidationError, match="real_field conclusion requires real_field records"):
        FieldValidationSummary(
            summary_id="summary-field",
            product_version="1.0.0",
            generated_at=_NOW,
            conclusion_class="real_field",
            records=[synthetic_record],
            notes="cannot claim field from synthetic",
        )


def test_summary_keeps_tiers_separate_and_reports_counts() -> None:
    synthetic = FieldValidationRecord(
        record_id="rec-synthetic",
        evidence=_synthetic_evidence(),
        conducted_at=_NOW,
        summary="synthetic",
    )
    staging = FieldValidationRecord(
        record_id="rec-staging",
        evidence=_staging_evidence(),
        conducted_at=_NOW,
        summary="staging",
    )
    summary = FieldValidationSummary(
        summary_id="summary-mixed",
        product_version="1.0.0",
        generated_at=_NOW,
        conclusion_class="staging",
        records=[synthetic, staging],
        notes="mixed lower tiers, no field conclusion",
    )
    assert summary.record_count_by_class["synthetic_fixture"] == 1
    assert summary.record_count_by_class["staging"] == 1
    assert summary.record_count_by_class["real_field"] == 0
