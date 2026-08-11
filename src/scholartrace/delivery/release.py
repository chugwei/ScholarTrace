"""Atomic local release pointers and rollback operations."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from scholartrace.delivery.manifest import calculate_manifest_sha256, verify_delivery_tree
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
        if report.manifest_sha256 != calculate_manifest_sha256(manifest):
            raise ReleaseConflictError("delivery manifest hash changed during activation")
        state = self.load()
        pointer = ReleasePointer(
            release_id=release_id,
            delivery_id=manifest.delivery_id,
            manifest_sha256=report.manifest_sha256,
            root_relpath=root_relpath,
            activated_at=datetime.now(UTC),
        )
        if state.active is not None and state.active.release_id == release_id:
            return state
        history = [*state.history, pointer]
        next_state = ReleaseState(active=pointer, previous=state.active, history=history)
        self._save(next_state)
        return next_state

    def rollback(self) -> ReleaseState:
        state = self.load()
        if state.previous is None:
            raise ReleaseConflictError("no previous release is available for rollback")
        next_state = ReleaseState(
            active=state.previous,
            previous=state.active,
            history=[*state.history, state.previous],
        )
        self._save(next_state)
        return next_state
