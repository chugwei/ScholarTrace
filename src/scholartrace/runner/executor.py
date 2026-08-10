"""Asynchronous, staging-based execution for controlled runs."""

from __future__ import annotations

import os
import queue
import shutil
import subprocess
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError
from contextlib import suppress
from pathlib import Path

from scholartrace.persistence.runner_repository import (
    ControlledRunRepository,
)
from scholartrace.runner.policy import CommandPolicy, DockerCommandBuilder
from scholartrace.schemas import ControlledRunEvent, ControlledRunRecord


class RunExecutorError(RuntimeError):
    """Raised when a controlled run cannot be started or published safely."""


LogCallback = Callable[[ControlledRunEvent], None]


class RunExecutor:
    """Run allowlisted commands in per-run staging directories.

    The executor never uses a shell and never publishes output from a failed,
    cancelled, timed-out, or log-limit-exceeded process.
    """

    def __init__(
        self,
        repository: ControlledRunRepository,
        *,
        workspace_root: Path,
        artifact_root: Path,
        input_root: Path | None = None,
        max_workers: int = 2,
        policy: CommandPolicy | None = None,
    ) -> None:
        if max_workers < 1:
            raise ValueError("max_workers must be positive")
        self._repository = repository
        self._workspace_root = workspace_root.expanduser().resolve()
        self._artifact_root = artifact_root.expanduser().resolve()
        self._input_root = input_root.expanduser().resolve() if input_root else None
        self._workspace_root.mkdir(parents=True, exist_ok=True)
        self._artifact_root.mkdir(parents=True, exist_ok=True)
        if self._input_root:
            self._input_root.mkdir(parents=True, exist_ok=True)
        self._policy = policy or CommandPolicy()
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="scholartrace")
        self._futures: dict[str, Future[ControlledRunRecord]] = {}
        self._cancel_events: dict[str, threading.Event] = {}
        self._processes: dict[str, subprocess.Popen[bytes]] = {}
        self._callbacks: dict[str, LogCallback | None] = {}
        self._lock = threading.RLock()

    def start(
        self,
        project_id: str,
        execution_id: str,
        *,
        on_event: LogCallback | None = None,
    ) -> ControlledRunRecord:
        """Start a queued run and return its persisted running state."""

        record = self._repository.get_run(project_id, execution_id)
        with self._lock:
            if record.status == "running" and execution_id in self._futures:
                return record
            if record.status != "queued":
                raise RunExecutorError(
                    f"run {execution_id!r} cannot start from status {record.status!r}"
                )
            running = self._repository.mark_running(project_id, execution_id)
            cancel_event = threading.Event()
            self._cancel_events[execution_id] = cancel_event
            self._callbacks[execution_id] = on_event
            try:
                future = self._pool.submit(
                    self._execute,
                    running,
                    cancel_event,
                )
            except Exception as error:
                self._repository.finish_run(
                    project_id,
                    execution_id,
                    status="failed",
                    error=f"executor submission failed: {error}",
                )
                raise RunExecutorError("controlled run submission failed") from error
            self._futures[execution_id] = future
            return running

    def cancel(self, project_id: str, execution_id: str) -> ControlledRunRecord:
        """Request cancellation; the worker persists the final state."""

        record = self._repository.get_run(project_id, execution_id)
        if record.status == "queued":
            return self._repository.finish_run(
                project_id,
                execution_id,
                status="cancelled",
                error="cancelled before start",
            )
        if record.status != "running":
            return record
        with self._lock:
            event = self._cancel_events.get(execution_id)
            if event is None:
                raise RunExecutorError(f"run {execution_id!r} has no active worker")
            event.set()
            process = self._processes.get(execution_id)
            if process is not None and process.poll() is None:
                _terminate_process(process)
        return self.wait(project_id, execution_id)

    def wait(
        self,
        project_id: str,
        execution_id: str,
        *,
        timeout: float | None = None,
    ) -> ControlledRunRecord:
        """Wait for a worker or return an already persisted terminal state."""

        with self._lock:
            future = self._futures.get(execution_id)
        if future is None:
            return self._repository.get_run(project_id, execution_id)
        try:
            future.result(timeout=timeout)
        except TimeoutError:
            raise
        return self._repository.get_run(project_id, execution_id)

    def shutdown(self, *, wait: bool = True) -> None:
        self._pool.shutdown(wait=wait)

    def _execute(
        self,
        record: ControlledRunRecord,
        cancel_event: threading.Event,
    ) -> ControlledRunRecord:
        spec = record.spec
        run_root = self._workspace_root / record.execution_id
        workspace = run_root / spec.workspace_relpath
        output_dir = workspace / spec.output_relpath
        if spec.backend == "docker":
            output_dir = run_root / "docker-output"
        log_path = run_root / "run.log"
        staging_relpath = run_root.relative_to(self._workspace_root).as_posix()
        log_relpath = log_path.relative_to(self._workspace_root).as_posix()
        process: subprocess.Popen[bytes] | None = None
        return_code: int | None = None
        failure_reason: str | None = None
        timed_out = False
        log_size = 0
        try:
            if run_root.exists():
                raise RunExecutorError("per-run staging directory already exists")
            run_root.mkdir(parents=True)
            workspace.mkdir(parents=True)
            output_dir.mkdir(parents=True)
            self._stage_inputs(spec.input_relpaths, workspace)
            self._emit(record, "system", "process:starting")
            if cancel_event.is_set():
                raise _CancelledBeforeStart
            if spec.backend == "docker":
                command = DockerCommandBuilder().build(
                    spec,
                    workspace=workspace,
                    outputs=output_dir,
                    policy=self._policy,
                )
            else:
                command = self._policy.validate(spec.command)
            process = subprocess.Popen(
                command,
                cwd=workspace,
                env=_safe_environment(spec.environment),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=False,
                start_new_session=os.name != "nt",
                creationflags=(
                    getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
                ),
            )
            with self._lock:
                self._processes[record.execution_id] = process
            output_queue: queue.Queue[bytes | None] = queue.Queue()
            reader = threading.Thread(
                target=_read_output,
                args=(process.stdout, output_queue),
                daemon=True,
            )
            reader.start()
            deadline = time.monotonic() + spec.limits.timeout_seconds
            output_closed = False
            with log_path.open("wb") as log_file:
                while not output_closed or process.poll() is None:
                    if cancel_event.is_set() and process.poll() is None:
                        failure_reason = "cancelled by caller"
                        _terminate_process(process)
                    elif time.monotonic() >= deadline and process.poll() is None:
                        timed_out = True
                        failure_reason = "run exceeded timeout_seconds"
                        _terminate_process(process)
                    try:
                        chunk = output_queue.get(timeout=0.05)
                    except queue.Empty:
                        continue
                    if chunk is None:
                        output_closed = True
                        continue
                    remaining = spec.limits.max_log_bytes - log_size
                    if remaining <= 0:
                        failure_reason = "run exceeded max_log_bytes"
                        _terminate_process(process)
                        continue
                    accepted = chunk[:remaining]
                    log_file.write(accepted)
                    log_file.flush()
                    log_size += len(accepted)
                    self._emit(record, "stdout", accepted.decode("utf-8", errors="replace"))
                    if len(accepted) < len(chunk):
                        failure_reason = "run exceeded max_log_bytes"
                        _terminate_process(process)
                return_code = process.wait()
            reader.join(timeout=1)
            with self._lock:
                self._processes.pop(record.execution_id, None)
            if cancel_event.is_set() and failure_reason is None:
                failure_reason = "cancelled by caller"
            if timed_out:
                status = "timed_out"
            elif failure_reason is not None:
                status = "cancelled" if failure_reason == "cancelled by caller" else "failed"
            elif return_code == 0:
                if _directory_size(output_dir) > spec.limits.max_output_bytes:
                    status = "failed"
                    failure_reason = "run exceeded max_output_bytes"
                else:
                    published = self._publish_output(record, output_dir)
                    return self._repository.finish_run(
                        record.project_id,
                        record.execution_id,
                        status="succeeded",
                        exit_code=return_code,
                        log_relpath=log_relpath,
                        staging_relpath=staging_relpath,
                        published_relpath=published,
                    )
            else:
                status = "failed"
                failure_reason = f"process exited with code {return_code}"
            return self._repository.finish_run(
                record.project_id,
                record.execution_id,
                status=status,
                exit_code=return_code,
                error=failure_reason,
                log_relpath=log_relpath,
                staging_relpath=staging_relpath,
            )
        except _CancelledBeforeStart:
            return self._repository.finish_run(
                record.project_id,
                record.execution_id,
                status="cancelled",
                error="cancelled before process start",
                staging_relpath=staging_relpath,
            )
        except Exception as error:
            if process is not None and process.poll() is None:
                _terminate_process(process)
            with self._lock:
                self._processes.pop(record.execution_id, None)
            return self._repository.finish_run(
                record.project_id,
                record.execution_id,
                status="failed",
                exit_code=return_code,
                error=str(error),
                log_relpath=log_relpath if log_path.exists() else None,
                staging_relpath=staging_relpath if run_root.exists() else None,
            )

    def _stage_inputs(self, input_relpaths: list[str], workspace: Path) -> None:
        if not input_relpaths:
            return
        if self._input_root is None:
            raise RunExecutorError("input_root is required when input_relpaths are specified")
        for relative in input_relpaths:
            source = (self._input_root / relative).resolve()
            _assert_inside(source, self._input_root)
            destination = workspace / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                shutil.copytree(source, destination)
            elif source.is_file():
                shutil.copy2(source, destination)
            else:
                raise RunExecutorError(f"input path does not exist: {relative}")

    def _publish_output(self, record: ControlledRunRecord, output_dir: Path) -> str:
        final = self._artifact_root / record.project_id / record.execution_id
        if final.exists():
            raise RunExecutorError("formal artifact destination already exists")
        final.parent.mkdir(parents=True, exist_ok=True)
        temporary = final.parent / f".{record.execution_id}.publishing"
        if temporary.exists():
            raise RunExecutorError("stale artifact publishing directory exists")
        try:
            shutil.copytree(output_dir, temporary)
            os.replace(temporary, final)
        except Exception:
            if temporary.exists():
                shutil.rmtree(temporary, ignore_errors=True)
            raise
        return final.relative_to(self._artifact_root).as_posix()

    def _emit(self, record: ControlledRunRecord, stream: str, message: str) -> None:
        event = self._repository.append_event(
            record.project_id,
            record.execution_id,
            stream=stream,
            message=message,
        )
        callback = self._callbacks.get(record.execution_id)
        if callback is not None:
            with suppress(Exception):
                callback(event)


class _CancelledBeforeStart(Exception):
    pass


def _read_output(pipe: object, output_queue: queue.Queue[bytes | None]) -> None:
    stream = pipe
    while True:
        chunk = stream.read(4096)  # type: ignore[union-attr]
        if not chunk:
            output_queue.put(None)
            return
        output_queue.put(chunk)


def _safe_environment(overrides: dict[str, str]) -> dict[str, str]:
    """Build a minimal environment and avoid inheriting unrelated secrets."""

    environment = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1",
    }
    for key in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME"):
        value = os.environ.get(key)
        if value:
            environment[key] = value
    environment.update(overrides)
    return environment


def _assert_inside(path: Path, root: Path) -> None:
    try:
        path.relative_to(root)
    except ValueError as error:
        raise RunExecutorError("path escapes the configured runner root") from error


def _directory_size(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=1)
