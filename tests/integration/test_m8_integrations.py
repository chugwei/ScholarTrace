import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from scholartrace.integrations import (
    DVCDataVersionAdapter,
    JsonTrackingAdapter,
    MLflowTrackingAdapter,
)
from scholartrace.schemas import ControlledRunRecord, ControlledRunSpec, ResourceLimits

CREATED_AT = datetime(2026, 8, 11, tzinfo=UTC)


def record() -> ControlledRunRecord:
    spec = ControlledRunSpec(
        execution_id="exec-track",
        project_id="lychee-m8",
        plan_id="plan-m8-v1",
        matrix_entry_id="matrix-m8",
        command=["python", "runner_script.py"],
        input_relpaths=["runner_script.py"],
        limits=ResourceLimits(timeout_seconds=30, memory_mb=256),
        created_by="researcher-001",
        created_at=CREATED_AT,
    )
    return ControlledRunRecord(
        execution_id="exec-track",
        project_id="lychee-m8",
        plan_id="plan-m8-v1",
        matrix_entry_id="matrix-m8",
        status="succeeded",
        backend="local",
        command_sha256="a" * 64,
        spec=spec,
        event_count=3,
        created_at=CREATED_AT,
    )


def test_json_tracking_is_deterministic_and_offline(tmp_path: Path) -> None:
    attempt = JsonTrackingAdapter(tmp_path / "tracking").record_run(record())
    assert attempt.status == "recorded"
    payload = json.loads((tmp_path / "tracking" / "exec-track.json").read_text(encoding="utf-8"))
    assert payload["command_sha256"] == "a" * 64
    assert "metric" not in payload


def test_mlflow_adapter_reports_real_availability_boundary() -> None:
    adapter = MLflowTrackingAdapter()
    attempt = adapter.record_run(record())
    if adapter.available:
        assert attempt.status in {"recorded", "failed"}
    else:
        assert attempt.status == "unavailable"
        assert "not installed" in (attempt.reason or "")


def test_dvc_manifest_hash_and_path_checks(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    data_file = data_root / "labels.json"
    data_file.write_text('{"labels": []}\n', encoding="utf-8")
    digest = hashlib.sha256(data_file.read_bytes()).hexdigest()
    manifest = tmp_path / "labels.dvc.json"
    manifest.write_text(
        json.dumps({"path": "labels.json", "sha256": digest}),
        encoding="utf-8",
    )
    verified = DVCDataVersionAdapter(data_root).verify_manifest(manifest)
    assert verified.status == "verified"
    assert verified.actual_sha256 == digest

    manifest.write_text(
        json.dumps({"path": "labels.json", "sha256": "0" * 64}),
        encoding="utf-8",
    )
    assert DVCDataVersionAdapter(data_root).verify_manifest(manifest).status == "mismatch"

    manifest.write_text(
        json.dumps({"path": "../private.json", "sha256": digest}),
        encoding="utf-8",
    )
    escaped = DVCDataVersionAdapter(data_root).verify_manifest(manifest)
    assert escaped.status == "mismatch"
    assert "escape" in (escaped.reason or "")
