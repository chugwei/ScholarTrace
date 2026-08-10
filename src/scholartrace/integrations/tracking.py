"""Replaceable offline, MLflow and DVC integration boundaries."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from scholartrace.identifiers import validate_identifier
from scholartrace.schemas import ControlledRunRecord, DVCDataVersionCheck, TrackingAttempt
from scholartrace.schemas.runner import validate_relative_path


class TrackingIntegrationError(RuntimeError):
    """Raised for invalid integration inputs, not for optional availability."""


class RunTrackingAdapter(Protocol):
    def record_run(self, record: ControlledRunRecord) -> TrackingAttempt:
        """Record only run provenance and status."""


class JsonTrackingAdapter:
    """Deterministic local fallback that never requires MLflow."""

    provider = "json"

    def __init__(self, root: Path) -> None:
        self._root = root.expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def record_run(self, record: ControlledRunRecord) -> TrackingAttempt:
        execution_id = validate_identifier(record.execution_id)
        payload = {
            "execution_id": execution_id,
            "project_id": record.project_id,
            "plan_id": record.plan_id,
            "matrix_entry_id": record.matrix_entry_id,
            "status": record.status,
            "backend": record.backend,
            "command_sha256": record.command_sha256,
            "published_relpath": record.published_relpath,
            "event_count": record.event_count,
        }
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        destination = self._root / f"{execution_id}.json"
        temporary = destination.with_suffix(".json.tmp")
        temporary.write_text(serialized, encoding="utf-8", newline="")
        os.replace(temporary, destination)
        return TrackingAttempt(
            execution_id=execution_id,
            provider=self.provider,
            status="recorded",
            record_path=destination.as_posix(),
            recorded_at=_utc_now(),
        )


class MLflowTrackingAdapter:
    """Lazy MLflow adapter with an honest offline/unavailable result."""

    provider = "mlflow"

    def __init__(self, tracking_uri: str | None = None) -> None:
        self._tracking_uri = tracking_uri

    @property
    def available(self) -> bool:
        return importlib.util.find_spec("mlflow") is not None

    def record_run(self, record: ControlledRunRecord) -> TrackingAttempt:
        if not self.available:
            return TrackingAttempt(
                execution_id=record.execution_id,
                provider=self.provider,
                status="unavailable",
                reason="mlflow package is not installed; JSON tracking remains available",
                recorded_at=_utc_now(),
            )
        try:
            import mlflow

            if self._tracking_uri:
                mlflow.set_tracking_uri(self._tracking_uri)
            with mlflow.start_run(run_name=record.execution_id):
                mlflow.set_tags(
                    {
                        "project_id": record.project_id,
                        "plan_id": record.plan_id,
                        "matrix_entry_id": record.matrix_entry_id,
                        "controlled_status": record.status,
                    }
                )
                mlflow.log_param("command_sha256", record.command_sha256)
            return TrackingAttempt(
                execution_id=record.execution_id,
                provider=self.provider,
                status="recorded",
                recorded_at=_utc_now(),
            )
        except Exception as error:
            return TrackingAttempt(
                execution_id=record.execution_id,
                provider=self.provider,
                status="failed",
                reason=f"MLflow call failed: {error}",
                recorded_at=_utc_now(),
            )


class DVCDataVersionAdapter:
    """Verify a DVC-style JSON manifest without invoking the DVC CLI."""

    provider = "dvc_manifest"

    def __init__(self, data_root: Path) -> None:
        self._data_root = data_root.expanduser().resolve()

    def verify_manifest(self, manifest_path: Path) -> DVCDataVersionCheck:
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            raw_path = str(payload["path"])
            expected = str(payload["sha256"])
        except (
            OSError,
            UnicodeError,
            KeyError,
            TypeError,
            json.JSONDecodeError,
        ) as error:
            return DVCDataVersionCheck(
                path=manifest_path.as_posix(),
                expected_sha256="0" * 64,
                status="unavailable",
                source="unavailable",
                reason=f"DVC manifest could not be read: {error}",
                checked_at=_utc_now(),
            )
        try:
            relative = validate_relative_path(raw_path, field_name="DVC path")
        except ValueError as error:
            if len(expected) == 64 and all(
                character in "0123456789abcdef" for character in expected
            ):
                return DVCDataVersionCheck(
                    path=raw_path,
                    expected_sha256=expected,
                    status="mismatch",
                    source=self.provider,
                    reason=str(error),
                    checked_at=_utc_now(),
                )
            return DVCDataVersionCheck(
                path=raw_path,
                expected_sha256="0" * 64,
                status="unavailable",
                source="unavailable",
                reason=f"DVC path or hash is invalid: {error}",
                checked_at=_utc_now(),
            )
        if len(expected) != 64 or any(
            character not in "0123456789abcdef" for character in expected
        ):
            return DVCDataVersionCheck(
                path=relative,
                expected_sha256="0" * 64,
                status="unavailable",
                source="unavailable",
                reason="DVC manifest sha256 is invalid",
                checked_at=_utc_now(),
            )
        data_path = (self._data_root / relative).resolve()
        try:
            data_path.relative_to(self._data_root)
        except ValueError:
            return DVCDataVersionCheck(
                path=relative,
                expected_sha256=expected,
                status="mismatch",
                source=self.provider,
                reason="DVC path escapes the configured data root",
                checked_at=_utc_now(),
            )
        if not data_path.is_file():
            return DVCDataVersionCheck(
                path=relative,
                expected_sha256=expected,
                status="unavailable",
                source="unavailable",
                reason="DVC data file is not present",
                checked_at=_utc_now(),
            )
        actual = _sha256(data_path)
        return DVCDataVersionCheck(
            path=relative,
            expected_sha256=expected,
            actual_sha256=actual,
            status="verified" if actual == expected else "mismatch",
            source=self.provider,
            reason=None if actual == expected else "local file hash differs from DVC manifest",
            checked_at=_utc_now(),
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> datetime:
    return datetime.now(UTC)
