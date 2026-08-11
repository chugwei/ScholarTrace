import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import URLError

import pytest

from scholartrace.delivery import (
    ReleaseConflictError,
    ReleaseStore,
    probe_health,
    verify_delivery_tree,
    write_sha256sums,
)
from scholartrace.schemas import HealthProbeResult
from scholartrace.schemas.delivery import DeliveryManifest

ROOT = Path(__file__).parents[2]
EXAMPLE_ROOT = ROOT / "examples" / "delivery"


def _example_manifest() -> DeliveryManifest:
    return DeliveryManifest.model_validate_json(
        (EXAMPLE_ROOT / "delivery-manifest.json").read_text(encoding="utf-8")
    )


def test_sha256sums_rebuild_and_release_rollback(tmp_path: Path) -> None:
    manifest = _example_manifest()
    release_one = tmp_path / "releases" / "one"
    release_two = tmp_path / "releases" / "two"
    shutil.copytree(EXAMPLE_ROOT, release_one)
    shutil.copytree(EXAMPLE_ROOT, release_two)
    checksum_hash = write_sha256sums(release_one, manifest)
    assert len(checksum_hash) == 64
    checksum = release_one / "SHA256SUMS.txt"
    assert checksum.is_file()
    assert "README.md" in checksum.read_text(encoding="utf-8")
    assert verify_delivery_tree(release_one, manifest).passed

    store = ReleaseStore(tmp_path / "state" / "release.json")
    first = store.activate("release-one", manifest, release_one, root_relpath="releases/one")
    assert first.active is not None and first.active.release_id == "release-one"
    second = store.activate("release-two", manifest, release_two, root_relpath="releases/two")
    assert second.previous is not None and second.previous.release_id == "release-one"
    rolled_back = store.rollback()
    assert rolled_back.active is not None and rolled_back.active.release_id == "release-one"
    assert rolled_back.previous is not None and rolled_back.previous.release_id == "release-two"

    (release_two / "README.md").write_text("tampered", encoding="utf-8")
    with pytest.raises(ReleaseConflictError, match="failed verification"):
        store.activate("release-two-bad", manifest, release_two, root_relpath="releases/two")
    assert store.load().active is not None
    assert store.load().active.release_id == "release-one"


def test_health_probe_preserves_success_and_network_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        status = 200

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"status":"ok","version":"fixture"}'

    monkeypatch.setattr(
        "scholartrace.delivery.monitoring.urlopen", lambda *_args, **_kwargs: FakeResponse()
    )
    success = probe_health("http://fixture/health")
    assert success.ok is True
    assert success.payload["status"] == "ok"

    def fail(*_args: object, **_kwargs: object) -> None:
        raise URLError("offline")

    monkeypatch.setattr("scholartrace.delivery.monitoring.urlopen", fail)
    failure = probe_health("http://fixture/health")
    assert failure.ok is False
    assert "URLError" in (failure.error or "")

    class InvalidPayload(FakeResponse):
        def read(self) -> bytes:
            return b'["not", "an", "object"]'

    monkeypatch.setattr(
        "scholartrace.delivery.monitoring.urlopen", lambda *_args, **_kwargs: InvalidPayload()
    )
    malformed = probe_health("http://fixture/health")
    assert malformed.ok is False
    assert malformed.error == "health response must be a JSON object"


def test_health_probe_result_is_structured() -> None:
    result = HealthProbeResult(
        endpoint="http://fixture/health",
        status_code=503,
        ok=False,
        error="HTTP 503",
        checked_at=datetime.now(UTC),
    )
    assert json.loads(result.model_dump_json())["ok"] is False
