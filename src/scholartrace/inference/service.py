"""Inference service with a deterministic offline provider and strict provenance."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from scholartrace.delivery.manifest import verify_delivery_tree
from scholartrace.schemas.delivery import DeliveryEvidence, DeliveryManifest
from scholartrace.schemas.inference import InferenceRequest, InferenceResponse, Prediction


class InferenceContractError(ValueError):
    """Raised when an inference request cannot be proven against a delivery manifest."""


class Predictor(Protocol):
    """Replaceable model provider used after delivery provenance checks."""

    model_version: str

    def predict(self, payload: bytes, *, evidence: DeliveryEvidence) -> list[Prediction]:
        """Return predictions without changing delivery or research state."""


class FixturePredictor:
    """Deterministic offline provider that never represents a field model."""

    model_version = "fixture-1"

    def predict(self, payload: bytes, *, evidence: DeliveryEvidence) -> list[Prediction]:
        bucket = hashlib.sha256(payload).hexdigest()[:8]
        return [
            Prediction(
                label=f"fixture_input_{bucket}",
                score=1.0,
                evidence=evidence,
            )
        ]


class InferenceService:
    """Verify a delivery tree before invoking a replaceable predictor."""

    def __init__(
        self,
        delivery_root: Path,
        manifest: DeliveryManifest,
        *,
        predictor: Predictor | None = None,
    ) -> None:
        self._delivery_root = delivery_root.expanduser()
        self._manifest = manifest
        self._predictor = predictor or FixturePredictor()

    def predict(self, request: InferenceRequest) -> InferenceResponse:
        request.validate_path()
        if (
            request.model_version is not None
            and request.model_version != self._manifest.model_card.model_version
        ):
            raise InferenceContractError(
                "requested model version does not match the delivery manifest"
            )
        if self._predictor.model_version != self._manifest.model_card.model_version:
            raise InferenceContractError(
                "predictor model version does not match the delivery manifest"
            )
        artifact = next(
            (
                item
                for item in self._manifest.artifacts
                if item.relative_path == request.input_relpath
            ),
            None,
        )
        if artifact is None:
            raise InferenceContractError("inference input is not listed in the delivery manifest")
        if request.input_sha256 != artifact.sha256:
            raise InferenceContractError("inference input SHA-256 does not match the manifest")
        report = verify_delivery_tree(self._delivery_root, self._manifest)
        if not report.passed:
            raise InferenceContractError("delivery tree failed manifest verification")
        input_path = (self._delivery_root / request.input_relpath).resolve()
        payload = input_path.read_bytes()
        actual_sha256 = hashlib.sha256(payload).hexdigest()
        if actual_sha256 != request.input_sha256:
            raise InferenceContractError("inference input SHA-256 does not match the request")
        warnings: list[str] = []
        if self._manifest.status != "verified":
            warnings.append("delivery manifest is not approved for field use")
        if self._manifest.evidence.evidence_class != "real_field":
            warnings.append(
                "prediction evidence is "
                f"{self._manifest.evidence.evidence_class}; it is not a field result"
            )
        predictions = self._predictor.predict(payload, evidence=self._manifest.evidence)
        return InferenceResponse(
            request_id=request.request_id,
            delivery_id=self._manifest.delivery_id,
            manifest_sha256=report.manifest_sha256,
            model_version=self._manifest.model_card.model_version,
            status="predicted",
            predictions=predictions,
            warnings=warnings,
            created_at=datetime.now(UTC),
        )
