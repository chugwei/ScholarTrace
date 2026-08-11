from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError

from scholartrace.delivery import (
    calculate_manifest_sha256,
    verify_delivery_tree,
    write_delivery_manifest,
)
from scholartrace.schemas import (
    DataCard,
    DeliveryArtifact,
    DeliveryEvidence,
    DeliveryManifest,
    ModelCard,
    ModelMetric,
)


def _evidence() -> DeliveryEvidence:
    return DeliveryEvidence(
        evidence_class="synthetic_fixture",
        source_ref="tests/fixtures/projects/lychee-pest-detection.json",
    )


def _manifest(artifact: DeliveryArtifact) -> DeliveryManifest:
    evidence = _evidence()
    return DeliveryManifest(
        delivery_id="delivery-lychee-demo",
        product_version="0.11.0",
        source_revision="a" * 40,
        generated_at=datetime(2026, 8, 11, tzinfo=UTC),
        entrypoint="scholartrace.inference:predict",
        install_command="uv sync --frozen",
        model_card=ModelCard(
            model_card_id="model-card-lychee",
            model_name="fixture-pest-detector",
            model_version="fixture-1",
            task="pest detection",
            intended_use="offline contract demonstration",
            out_of_scope_uses=["field deployment", "regulatory decisions"],
            training_data_ref="fixture://lychee-pest-detection/train",
            evaluation_data_ref="fixture://lychee-pest-detection/validation",
            metrics=[
                ModelMetric(
                    name="precision",
                    value=1.0,
                    split="fixture",
                    verification_status="verified",
                    evidence=evidence,
                )
            ],
            limitations=["synthetic data only"],
            ethical_considerations=["no personal data is included"],
            evidence=evidence,
        ),
        data_card=DataCard(
            data_card_id="data-card-lychee",
            dataset_name="lychee pest fixture",
            dataset_version="fixture-1",
            purpose="offline schema and inference smoke tests",
            source_description="de-identified synthetic fixture",
            license_or_access="repository test fixture",
            collection_protocol_ref="fixture://protocol/offline",
            preprocessing=["decode JSON fixture", "do not infer field results"],
            split_strategy="fixed fixture split",
            known_limitations=["not a field sample"],
            privacy_review="synthetic and de-identified",
            evidence=evidence,
        ),
        artifacts=[artifact],
        evidence=evidence,
    )


def test_delivery_manifest_round_trip_and_tamper_detection(tmp_path: Path) -> None:
    content = b"synthetic delivery readme\n"
    artifact_path = tmp_path / "README.delivery.md"
    artifact_path.write_bytes(content)
    artifact = DeliveryArtifact(
        relative_path=artifact_path.name,
        sha256=sha256(content).hexdigest(),
        size_bytes=len(content),
        media_type="text/markdown",
    )
    manifest = _manifest(artifact)
    first_hash = calculate_manifest_sha256(manifest)
    assert first_hash == calculate_manifest_sha256(manifest.model_copy(deep=True))
    manifest_path = tmp_path / "delivery-manifest.json"
    assert (
        write_delivery_manifest(manifest_path, manifest)
        == sha256(manifest_path.read_bytes()).hexdigest()
    )
    report = verify_delivery_tree(tmp_path, manifest)
    assert report.passed is True
    assert report.entries[0].status == "passed"

    artifact_path.write_bytes(b"tampered\n")
    tampered = verify_delivery_tree(tmp_path, manifest)
    assert tampered.passed is False
    assert tampered.entries[0].status == "hash_mismatch"


def test_delivery_manifest_rejects_unverifiable_field_claims_and_unsafe_paths() -> None:
    with pytest.raises(ValidationError, match="real_field evidence"):
        DeliveryEvidence(evidence_class="real_field", source_ref="field/run-001")
    with pytest.raises(ValidationError, match="synthetic_fixture"):
        manifest = _manifest(
            DeliveryArtifact(
                relative_path="README.md",
                sha256="a" * 64,
                size_bytes=1,
                media_type="text/markdown",
            )
        )
        DeliveryManifest.model_validate({**manifest.model_dump(), "status": "verified"})
    with pytest.raises(ValidationError, match="delivery artifact path"):
        DeliveryArtifact(
            relative_path="../outside.txt",
            sha256="a" * 64,
            size_bytes=1,
            media_type="text/plain",
        )


def test_delivery_manifest_requires_unique_artifacts() -> None:
    artifact = DeliveryArtifact(
        relative_path="README.md",
        sha256="a" * 64,
        size_bytes=1,
        media_type="text/markdown",
    )
    with pytest.raises(ValidationError, match="paths must be unique"):
        manifest = _manifest(artifact)
        DeliveryManifest.model_validate(
            {**manifest.model_dump(), "artifacts": [artifact.model_dump(), artifact.model_dump()]}
        )
