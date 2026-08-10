"""Persistence for controlled execution requests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from scholartrace.identifiers import validate_identifier
from scholartrace.persistence.database import create_sqlite_engine
from scholartrace.persistence.models import (
    ControlledRunRow,
    ExperimentPlanRow,
    ProjectRow,
)
from scholartrace.runner.policy import CommandPolicy
from scholartrace.schemas import ControlledRunRecord, ControlledRunSpec


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
            return _record_model(row)

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
            return [_record_model(row) for row in rows]


def _command_sha256(command: list[str]) -> str:
    payload = json.dumps(command, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _record_model(row: ControlledRunRow) -> ControlledRunRecord:
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
        created_at=row.created_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
    )
