import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from scholartrace.api import create_app
from scholartrace.cli import app
from scholartrace.delivery import write_delivery_manifest
from scholartrace.inference import InferenceContractError, InferenceService
from scholartrace.schemas import (
    DataCard,
    DeliveryArtifact,
    DeliveryEvidence,
    DeliveryManifest,
    InferenceRequest,
    ModelCard,
)


def _manifest(artifact: DeliveryArtifact) -> DeliveryManifest:
    evidence = DeliveryEvidence(
        evidence_class="synthetic_fixture",
        source_ref="tests/fixtures/projects/lychee-pest-detection.json",
    )
    return DeliveryManifest(
        delivery_id="delivery-inference-demo",
        product_version="0.11.0",
        source_revision="b" * 40,
        generated_at=datetime(2026, 8, 11, tzinfo=UTC),
        entrypoint="scholartrace.inference:predict",
        install_command="uv sync --frozen",
        model_card=ModelCard(
            model_card_id="model-card-inference",
            model_name="fixture-pest-detector",
            model_version="fixture-1",
            task="pest detection",
            intended_use="offline smoke tests",
            out_of_scope_uses=["field decisions"],
            training_data_ref="fixture://train",
            evaluation_data_ref="fixture://validation",
            limitations=["synthetic input"],
            ethical_considerations=["no personal data"],
            evidence=evidence,
        ),
        data_card=DataCard(
            data_card_id="data-card-inference",
            dataset_name="fixture input",
            dataset_version="fixture-1",
            purpose="offline inference smoke tests",
            source_description="synthetic bytes",
            license_or_access="repository fixture",
            collection_protocol_ref="fixture://protocol",
            preprocessing=["read bytes"],
            split_strategy="fixed",
            known_limitations=["not field data"],
            privacy_review="synthetic",
            evidence=evidence,
        ),
        artifacts=[artifact],
        evidence=evidence,
    )


def test_manifest_bound_fixture_inference_rejects_tampering(tmp_path: Path) -> None:
    payload = b"fixture-image-bytes"
    input_path = tmp_path / "sample-inputs" / "sample.bin"
    input_path.parent.mkdir()
    input_path.write_bytes(payload)
    manifest = _manifest(
        DeliveryArtifact(
            relative_path="sample-inputs/sample.bin",
            sha256=sha256(payload).hexdigest(),
            size_bytes=len(payload),
            media_type="application/octet-stream",
        )
    )
    response = InferenceService(tmp_path, manifest).predict(
        InferenceRequest(
            request_id="request-001",
            input_relpath="sample-inputs/sample.bin",
            input_sha256=sha256(payload).hexdigest(),
        )
    )
    assert response.status == "predicted"
    assert response.predictions[0].label.startswith("fixture_input_")
    assert any("not a field result" in warning for warning in response.warnings)

    with pytest.raises(InferenceContractError, match="manifest"):
        InferenceService(tmp_path, manifest).predict(
            InferenceRequest(
                request_id="request-wrong-hash",
                input_relpath="sample-inputs/sample.bin",
                input_sha256=sha256(b"another-input").hexdigest(),
            )
        )

    input_path.write_bytes(b"tampered")
    with pytest.raises(InferenceContractError, match="delivery tree"):
        InferenceService(tmp_path, manifest).predict(
            InferenceRequest(
                request_id="request-002",
                input_relpath="sample-inputs/sample.bin",
                input_sha256=sha256(payload).hexdigest(),
            )
        )


def test_configured_api_exposes_offline_inference_and_unconfigured_degrades(tmp_path: Path) -> None:
    payload = b"api-fixture"
    root = tmp_path / "delivery"
    input_path = root / "sample.bin"
    input_path.parent.mkdir()
    input_path.write_bytes(payload)
    manifest = _manifest(
        DeliveryArtifact(
            relative_path="sample.bin",
            sha256=sha256(payload).hexdigest(),
            size_bytes=len(payload),
            media_type="application/octet-stream",
        )
    )
    manifest_path = root / "delivery-manifest.json"
    write_delivery_manifest(manifest_path, manifest)
    configured = TestClient(
        create_app(
            tmp_path / "configured.db",
            delivery_root=root,
            delivery_manifest_path=manifest_path,
        )
    )
    result = configured.post(
        "/api/inference",
        json={
            "request_id": "request-api",
            "input_relpath": "sample.bin",
            "input_sha256": sha256(payload).hexdigest(),
        },
    )
    assert result.status_code == 200
    assert result.json()["status"] == "predicted"

    unconfigured = TestClient(create_app(tmp_path / "unconfigured.db"))
    assert (
        unconfigured.post(
            "/api/inference",
            json={
                "request_id": "request-api",
                "input_relpath": "sample.bin",
                "input_sha256": sha256(payload).hexdigest(),
            },
        ).status_code
        == 503
    )


def test_infer_cli_emits_traceable_response(tmp_path: Path) -> None:
    payload = b"cli-fixture"
    input_path = tmp_path / "sample.bin"
    input_path.write_bytes(payload)
    manifest = _manifest(
        DeliveryArtifact(
            relative_path="sample.bin",
            sha256=sha256(payload).hexdigest(),
            size_bytes=len(payload),
            media_type="application/octet-stream",
        )
    )
    manifest_path = tmp_path / "delivery-manifest.json"
    write_delivery_manifest(manifest_path, manifest)
    result = CliRunner().invoke(
        app,
        [
            "infer",
            "--manifest",
            str(manifest_path),
            "--delivery-root",
            str(tmp_path),
            "--input",
            "sample.bin",
            "--request-id",
            "request-cli",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["status"] == "predicted"
