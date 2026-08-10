"""Persistence for controlled execution requests."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from scholartrace.identifiers import validate_identifier
from scholartrace.persistence.database import create_sqlite_engine
from scholartrace.persistence.models import (
    ControlledRunEventRow,
    ControlledRunRow,
    ExperimentPlanRow,
    ProjectRow,
)
from scholartrace.runner.policy import CommandPolicy
from scholartrace.schemas import ControlledRunEvent, ControlledRunRecord, ControlledRunSpec

_TERMINAL_STATUSES = {"succeeded", "failed", "cancelled", "timed_out"}


class ControlledRunRepositoryError(RuntimeError):
    """Base error for controlled-run persistence."""


class ControlledRunConflictError(ControlledRunRepositoryError):
    """Raised when an execution identity is reused with different content."""


class ControlledRunRepository:
    """Create immutable queued runs only from frozen experiment plans."""

    def __init__(self, database_path: Path, *, policy: CommandPolicy | None = None) -> None:
        self._engine = create_sqlite_engine(database_path)
        self._policy = policy or CommandPolicy()

    def close(self) -> None:
        self._engine.dispose()

    def create_run(self, spec: ControlledRunSpec) -> ControlledRunRecord:
        self._policy.validate_spec(spec)
        project_id = validate_identifier(spec.project_id)
        plan_id = validate_identifier(spec.plan_id)
        execution_id = validate_identifier(spec.execution_id)
        with Session(self._engine) as session, session.begin():
            if session.get(ProjectRow, project_id) is None:
                raise ControlledRunRepositoryError(f"project {project_id!r} was not found")
            plan = session.get(ExperimentPlanRow, plan_id)
            if plan is None or plan.project_id != project_id:
                raise ControlledRunRepositoryError(
                    f"experiment plan {plan_id!r} was not found in project {project_id!r}"
                )
            if plan.status != "frozen":
                raise ControlledRunRepositoryError(
                    "controlled runs must reference a frozen experiment plan"
                )
            matrix_ids = {entry["matrix_entry_id"] for entry in plan.payload.get("matrix", [])}
            if spec.matrix_entry_id not in matrix_ids:
                raise ControlledRunRepositoryError(
                    f"matrix entry {spec.matrix_entry_id!r} is not part of the frozen plan"
                )
            existing = session.get(ControlledRunRow, execution_id)
            if existing is not None:
                persisted = _record_model(existing)
                if persisted.spec.model_dump(mode="json") != spec.model_dump(mode="json"):
                    raise ControlledRunConflictError(
                        f"execution_id {execution_id!r} has different content"
                    )
                return persisted
            normalized = spec.model_copy(
                update={
                    "project_id": project_id,
                    "plan_id": plan_id,
                    "execution_id": execution_id,
                }
            )
            command_sha256 = _command_sha256(normalized.command)
            row = ControlledRunRow(
                execution_id=execution_id,
                project_id=project_id,
                plan_id=plan_id,
                matrix_entry_id=normalized.matrix_entry_id,
                status="queued",
                backend=normalized.backend,
                command_sha256=command_sha256,
                payload=normalized.model_dump(mode="json"),
                created_at=normalized.created_at.replace(tzinfo=None),
            )
            session.add(row)
            try:
                session.flush()
            except IntegrityError as error:
                raise ControlledRunConflictError(
                    "controlled execution identity is already persisted"
                ) from error
            return _record_model(row)

    def get_run(self, project_id: str, execution_id: str) -> ControlledRunRecord:
        project_id = validate_identifier(project_id)
        execution_id = validate_identifier(execution_id)
        with Session(self._engine) as session:
            row = session.scalar(
                select(ControlledRunRow).where(
                    ControlledRunRow.project_id == project_id,
                    ControlledRunRow.execution_id == execution_id,
                )
            )
            if row is None:
                raise ControlledRunRepositoryError(
                    f"execution {execution_id!r} was not found in project {project_id!r}"
                )
            return _record_model(row, event_count=self._event_count(session, execution_id))

    def list_runs(self, project_id: str) -> list[ControlledRunRecord]:
        project_id = validate_identifier(project_id)
        with Session(self._engine) as session:
            if session.get(ProjectRow, project_id) is None:
                raise ControlledRunRepositoryError(f"project {project_id!r} was not found")
            rows = session.scalars(
                select(ControlledRunRow)
                .where(ControlledRunRow.project_id == project_id)
                .order_by(ControlledRunRow.created_at, ControlledRunRow.execution_id)
            ).all()
            return [
                _record_model(row, event_count=self._event_count(session, row.execution_id))
                for row in rows
            ]

    def mark_running(self, project_id: str, execution_id: str) -> ControlledRunRecord:
        """Transition a queued run to running, idempotently."""

        with Session(self._engine) as session, session.begin():
            row = self._row_for_project(session, project_id, execution_id)
            if row.status == "queued":
                row.status = "running"
                row.started_at = _utc_now_naive()
                self._append_event(session, row.execution_id, "system", "status:running")
            elif row.status != "running":
                raise ControlledRunRepositoryError(
                    f"run {row.execution_id!r} cannot start from status {row.status!r}"
                )
            return _record_model(row, event_count=self._event_count(session, row.execution_id))

    def finish_run(
        self,
        project_id: str,
        execution_id: str,
        *,
        status: str,
        exit_code: int | None = None,
        error: str | None = None,
        log_relpath: str | None = None,
        staging_relpath: str | None = None,
        published_relpath: str | None = None,
    ) -> ControlledRunRecord:
        """Persist one terminal outcome without deleting staging evidence."""

        if status not in _TERMINAL_STATUSES:
            raise ValueError("finish status must be a terminal controlled-run status")
        with Session(self._engine) as session, session.begin():
            row = self._row_for_project(session, project_id, execution_id)
            if row.status in _TERMINAL_STATUSES:
                if row.status != status:
                    raise ControlledRunRepositoryError(
                        f"run {row.execution_id!r} already finished as {row.status!r}"
                    )
            elif row.status not in {"queued", "running"}:
                raise ControlledRunRepositoryError(
                    f"run {row.execution_id!r} cannot finish from status {row.status!r}"
                )
            else:
                row.status = status
                row.exit_code = exit_code
                row.error = error
                row.log_relpath = log_relpath
                row.staging_relpath = staging_relpath
                row.published_relpath = published_relpath
                row.finished_at = _utc_now_naive()
                self._append_event(session, row.execution_id, "system", f"status:{status}")
            return _record_model(row, event_count=self._event_count(session, row.execution_id))

    def append_event(
        self,
        project_id: str,
        execution_id: str,
        *,
        stream: str,
        message: str,
    ) -> ControlledRunEvent:
        """Append one bounded event after checking project ownership."""

        with Session(self._engine) as session, session.begin():
            row = self._row_for_project(session, project_id, execution_id)
            event = self._append_event(session, row.execution_id, stream, message)
            return event

    def list_events(self, project_id: str, execution_id: str) -> list[ControlledRunEvent]:
        with Session(self._engine) as session:
            row = self._row_for_project(session, project_id, execution_id)
            events = session.scalars(
                select(ControlledRunEventRow)
                .where(ControlledRunEventRow.execution_id == row.execution_id)
                .order_by(ControlledRunEventRow.sequence)
            ).all()
            return [_event_model(event) for event in events]

    def _row_for_project(
        self, session: Session, project_id: str, execution_id: str
    ) -> ControlledRunRow:
        project_id = validate_identifier(project_id)
        execution_id = validate_identifier(execution_id)
        row = session.scalar(
            select(ControlledRunRow).where(
                ControlledRunRow.project_id == project_id,
                ControlledRunRow.execution_id == execution_id,
            )
        )
        if row is None:
            raise ControlledRunRepositoryError(
                f"execution {execution_id!r} was not found in project {project_id!r}"
            )
        return row

    @staticmethod
    def _event_count(session: Session, execution_id: str) -> int:
        return int(
            session.scalar(
                select(func.count())
                .select_from(ControlledRunEventRow)
                .where(ControlledRunEventRow.execution_id == execution_id)
            )
            or 0
        )

    @staticmethod
    def _append_event(
        session: Session,
        execution_id: str,
        stream: str,
        message: str,
    ) -> ControlledRunEvent:
        event_time = _utc_now()
        latest_sequence = session.scalar(
            select(func.max(ControlledRunEventRow.sequence)).where(
                ControlledRunEventRow.execution_id == execution_id
            )
        )
        sequence = (int(latest_sequence) if latest_sequence is not None else -1) + 1
        event = ControlledRunEvent(
            execution_id=execution_id,
            sequence=sequence,
            stream=stream,
            message=message,
            created_at=event_time,
        )
        session.add(
            ControlledRunEventRow(
                event_id=f"{execution_id}:{sequence}",
                execution_id=execution_id,
                sequence=sequence,
                stream=stream,
                message=message,
                created_at=event_time.replace(tzinfo=None),
            )
        )
        session.flush()
        return event


def _command_sha256(command: list[str]) -> str:
    payload = json.dumps(command, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _utc_now_naive() -> datetime:
    return _utc_now().replace(tzinfo=None)


def _record_model(row: ControlledRunRow, *, event_count: int = 0) -> ControlledRunRecord:
    spec = ControlledRunSpec.model_validate(row.payload)
    return ControlledRunRecord(
        execution_id=row.execution_id,
        project_id=row.project_id,
        plan_id=row.plan_id,
        matrix_entry_id=row.matrix_entry_id,
        status=row.status,
        backend=row.backend,
        command_sha256=row.command_sha256,
        spec=spec,
        exit_code=row.exit_code,
        error=row.error,
        log_relpath=row.log_relpath,
        staging_relpath=row.staging_relpath,
        published_relpath=row.published_relpath,
        event_count=event_count,
        created_at=row.created_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
    )


def _event_model(row: ControlledRunEventRow) -> ControlledRunEvent:
    return ControlledRunEvent(
        execution_id=row.execution_id,
        sequence=row.sequence,
        stream=row.stream,
        message=row.message,
        created_at=row.created_at,
    )
