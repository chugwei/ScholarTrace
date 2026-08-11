"""Deterministic delivery manifest serialization and file verification."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from scholartrace.schemas.delivery import (
    DeliveryManifest,
    DeliveryVerificationEntry,
    DeliveryVerificationReport,
)


def _canonical_manifest_json(manifest: DeliveryManifest) -> bytes:
    payload = manifest.model_dump(mode="json")
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        + b"\n"
    )


def calculate_manifest_sha256(manifest: DeliveryManifest) -> str:
    """Return the stable hash of a manifest independent of whitespace or key order."""

    return hashlib.sha256(_canonical_manifest_json(manifest)).hexdigest()


def write_delivery_manifest(path: Path, manifest: DeliveryManifest) -> str:
    """Atomically write a UTF-8 manifest and return its content SHA-256."""

    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    content = _canonical_manifest_json(manifest)
    digest = hashlib.sha256(content).hexdigest()
    with NamedTemporaryFile("wb", dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(content)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return digest


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_inside(root: Path, relative_path: str) -> Path:
    root = root.expanduser().resolve()
    candidate = (root / relative_path).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError(f"delivery artifact escapes root: {relative_path!r}")
    return candidate


def verify_delivery_tree(root: Path, manifest: DeliveryManifest) -> DeliveryVerificationReport:
    """Check every required and optional artifact against its manifest entry."""

    entries: list[DeliveryVerificationEntry] = []
    for artifact in manifest.artifacts:
        path = _resolve_inside(root, artifact.relative_path)
        if not path.is_file():
            entries.append(
                DeliveryVerificationEntry(
                    relative_path=artifact.relative_path,
                    status="missing",
                    expected_sha256=artifact.sha256,
                    expected_size_bytes=artifact.size_bytes,
                )
            )
            continue
        actual_size = path.stat().st_size
        actual_sha256 = _sha256(path)
        if actual_sha256 != artifact.sha256:
            status = "hash_mismatch"
        elif actual_size != artifact.size_bytes:
            status = "size_mismatch"
        else:
            status = "passed"
        entries.append(
            DeliveryVerificationEntry(
                relative_path=artifact.relative_path,
                status=status,
                expected_sha256=artifact.sha256,
                actual_sha256=actual_sha256,
                expected_size_bytes=artifact.size_bytes,
                actual_size_bytes=actual_size,
            )
        )
    return DeliveryVerificationReport(
        delivery_id=manifest.delivery_id,
        manifest_sha256=calculate_manifest_sha256(manifest),
        entries=entries,
        passed=all(entry.status == "passed" for entry in entries),
    )


def write_sha256sums(
    root: Path,
    manifest: DeliveryManifest,
    output_path: str = "SHA256SUMS.txt",
) -> str:
    """Write sorted hashes for all Manifest artifacts except the checksum file itself."""

    lines: list[str] = []
    for artifact in sorted(manifest.artifacts, key=lambda item: item.relative_path):
        if artifact.relative_path == output_path:
            continue
        path = _resolve_inside(root, artifact.relative_path)
        if not path.is_file():
            raise FileNotFoundError(path)
        lines.append(f"{_sha256(path)}  {artifact.relative_path}")
    destination = _resolve_inside(root, output_path)
    content = ("\n".join(lines) + "\n").encode("utf-8")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        "wb", dir=destination.parent, prefix=f".{destination.name}.", delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(content)
    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return hashlib.sha256(content).hexdigest()
