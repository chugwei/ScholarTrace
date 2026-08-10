"""Approved, isolated text repairs and regression execution."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

from scholartrace.runner.policy import CommandPolicy
from scholartrace.schemas import DebugCase, RegressionResult
from scholartrace.schemas.runner import validate_relative_path


class SafeRepairError(RuntimeError):
    """Raised when an approved repair would leave its isolated workspace."""


class SafeRepairWorkspace:
    """Copy a failed run into a branch-like directory before applying changes."""

    def __init__(
        self,
        *,
        source_root: Path,
        repair_root: Path,
        policy: CommandPolicy | None = None,
    ) -> None:
        self._source_root = source_root.expanduser().resolve()
        self._repair_root = repair_root.expanduser().resolve()
        self._policy = policy or CommandPolicy()
        self._repair_root.mkdir(parents=True, exist_ok=True)

    def create(self, case: DebugCase) -> Path:
        """Create an isolated copy of the failed run's working directory."""

        if case.status != "approved" or case.proposal is None:
            raise SafeRepairError(
                "a human-approved proposal is required before creating repair workspace"
            )
        if case.staging_relpath is None:
            raise SafeRepairError("DebugCase has no staging workspace to repair")
        source = (self._source_root / case.staging_relpath / "workspace").resolve()
        _assert_inside(source, self._source_root)
        if not source.is_dir():
            raise SafeRepairError("failed run workspace does not exist")
        if any(path.is_symlink() for path in source.rglob("*")):
            raise SafeRepairError("repair refuses to copy symbolic links")
        destination = self._repair_root / case.case_id
        if destination.exists():
            raise SafeRepairError("repair workspace already exists")
        shutil_copytree(source, destination)
        (destination / ".repair-branch").write_text(
            f"repair/{case.case_id}\n",
            encoding="utf-8",
        )
        return destination

    def apply(self, case: DebugCase, workspace: Path) -> Path:
        """Apply only approved text changes with optional source hash guards."""

        if case.status != "approved" or case.proposal is None:
            raise SafeRepairError("a human-approved proposal is required before applying a fix")
        workspace = workspace.expanduser().resolve()
        _assert_inside(workspace, self._repair_root)
        if not workspace.is_dir():
            raise SafeRepairError("repair workspace does not exist")
        for change in case.proposal.changes:
            relative = validate_relative_path(change.relative_path, field_name="repair path")
            destination = (workspace / relative).resolve()
            _assert_inside(destination, workspace)
            if destination.is_symlink():
                raise SafeRepairError("repair refuses to modify symbolic links")
            if change.expected_sha256 is not None and (
                not destination.is_file() or _sha256(destination) != change.expected_sha256
            ):
                raise SafeRepairError(
                    f"source hash guard failed for repair path {change.relative_path!r}"
                )
            if "\x00" in change.replacement_text:
                raise SafeRepairError("repair text must not contain NUL bytes")
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_name(f".{destination.name}.repair-tmp")
            temporary.write_text(change.replacement_text, encoding="utf-8", newline="")
            os.replace(temporary, destination)
        return workspace

    def run_regression(
        self,
        case: DebugCase,
        workspace: Path,
        *,
        timeout_seconds: float = 300,
    ) -> RegressionResult:
        """Run the approved regression command only inside the repair workspace."""

        if case.status != "approved" or case.proposal is None:
            raise SafeRepairError("a human-approved proposal is required before regression")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        workspace = workspace.expanduser().resolve()
        _assert_inside(workspace, self._repair_root)
        command = self._policy.validate(case.proposal.regression_command)
        try:
            completed = subprocess.run(
                command,
                cwd=workspace,
                env=_safe_environment(),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                shell=False,
                check=False,
            )
            output = (completed.stdout + completed.stderr)[-20_000:]
            return RegressionResult(
                status="passed" if completed.returncode == 0 else "failed",
                command=command,
                exit_code=completed.returncode,
                output_excerpt=output,
                checked_at=_utc_now(),
            )
        except subprocess.TimeoutExpired as error:
            output = str(error.output or "")[-20_000:]
            return RegressionResult(
                status="failed",
                command=command,
                exit_code=-1,
                output_excerpt=output,
                checked_at=_utc_now(),
            )


def shutil_copytree(source: Path, destination: Path) -> None:
    """Small wrapper kept explicit so copy direction is easy to audit."""

    import shutil

    shutil.copytree(source, destination)


def _assert_inside(path: Path, root: Path) -> None:
    try:
        path.relative_to(root)
    except ValueError as error:
        raise SafeRepairError("repair path escapes its isolated workspace") from error


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_environment() -> dict[str, str]:
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1",
    }
    for key in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME"):
        value = os.environ.get(key)
        if value:
            environment[key] = value
    return environment


def _utc_now():
    from datetime import UTC, datetime

    return datetime.now(UTC)
