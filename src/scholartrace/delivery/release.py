"""Atomic local release pointers and rollback operations."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from scholartrace.delivery.manifest import (
    calculate_manifest_sha256,
    resolve_inside,
    verify_delivery_tree,
)
from scholartrace.schemas.delivery import DeliveryManifest, ReleasePointer, ReleaseState


class ReleaseConflictError(ValueError):
    """Raised when activation or rollback would create an unverifiable state."""


class ReleaseStore:
    """Persist active/previous pointers with atomic JSON replacement."""

    def __init__(self, state_path: Path) -> None:
        self._state_path = state_path.expanduser()

    def load(self) -> ReleaseState:
        if not self._state_path.exists():
            return ReleaseState()
        return ReleaseState.model_validate_json(self._state_path.read_text(encoding="utf-8"))

    def _save(self, state: ReleaseState) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        content = (
            json.dumps(
                state.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            + b"\n"
        )
        with NamedTemporaryFile(
            "wb", dir=self._state_path.parent, prefix=f".{self._state_path.name}.", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
        try:
            os.replace(temporary, self._state_path)
        finally:
            temporary.unlink(missing_ok=True)

    def activate(
        self,
        release_id: str,
        manifest: DeliveryManifest,
        delivery_root: Path,
        *,
        root_relpath: str,
    ) -> ReleaseState:
        report = verify_delivery_tree(delivery_root, manifest)
        if not report.passed:
            raise ReleaseConflictError("cannot activate a delivery tree that failed verification")
        state = self.load()
        pointer = ReleasePointer(
            release_id=release_id,
            delivery_id=manifest.delivery_id,
            manifest_sha256=report.manifest_sha256,
            root_relpath=root_relpath,
            activated_at=datetime.now(UTC),
        )
        if state.active is not None and state.active.release_id == release_id:
            if (
                state.active.manifest_sha256 != pointer.manifest_sha256
                or state.active.root_relpath != root_relpath
            ):
                raise ReleaseConflictError(
                    "release_id is already active with a different manifest or root"
                )
            return state
        history = [*state.history, pointer]
        next_state = ReleaseState(active=pointer, previous=state.active, history=history)
        self._save(next_state)
        return next_state

    def rollback(self, base_root: Path, manifest: DeliveryManifest) -> ReleaseState:
        state = self.load()
        if state.previous is None:
            raise ReleaseConflictError("no previous release is available for rollback")
        if calculate_manifest_sha256(manifest) != state.previous.manifest_sha256:
            raise ReleaseConflictError("rollback manifest does not match the previous release")
        # Re-verify the previous tree before promoting it: the stored pointer was
        # validated at activation time, but the delivery files may have changed since.
        target_root = resolve_inside(base_root, state.previous.root_relpath)
        report = verify_delivery_tree(target_root, manifest)
        if not report.passed:
            raise ReleaseConflictError(
                "cannot rollback to a delivery tree that failed verification"
            )
        next_state = ReleaseState(
            active=state.previous,
            previous=state.active,
            history=[*state.history, state.previous],
        )
        self._save(next_state)
        return next_state
