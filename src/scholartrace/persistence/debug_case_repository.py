"""Transactional persistence and approval gates for DebugCase records."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from scholartrace.identifiers import validate_identifier
from scholartrace.persistence.database import create_sqlite_engine
from scholartrace.persistence.models import (
    ControlledRunRow,
    DebugCaseRow,
    ProjectRow,
)
from scholartrace.schemas import (
    DebugCase,
    DiagnosticFinding,
    DiagnosticHypothesis,
    RegressionResult,
    RepairProposal,
)


class DebugCaseRepositoryError(RuntimeError):
    """Base error for DebugCase persistence."""


class DebugCaseConflictError(DebugCaseRepositoryError):
    """Raised when a case identity or execution binding conflicts."""


class DebugCaseRepository:
    """Persist diagnosis as an explicit, human-gated state machine."""

    def __init__(self, database_path: Path) -> None:
        self._engine = create_sqlite_engine(database_path)

    def close(self) -> None:
        self._engine.dispose()

    def save_case(self, case: DebugCase) -> DebugCase:
        project_id = validate_identifier(case.project_id)
        case_id = validate_identifier(case.case_id)
        with Session(self._engine) as session, session.begin():
            self._require_project(session, project_id)
            run = session.get(ControlledRunRow, case.execution_id)
            if run is None or run.project_id != project_id:
                raise DebugCaseRepositoryError(
                    f"execution {case.execution_id!r} was not found in project {project_id!r}"
                )
            if run.status not in {"failed", "cancelled", "timed_out"}:
                raise DebugCaseRepositoryError(
                    "DebugCase requires a failed, cancelled, or timed-out run"
                )
            existing = session.get(DebugCaseRow, case_id)
            if existing is not None:
                persisted = _case_model(existing)
                if persisted.model_dump(mode="json") != case.model_dump(mode="json"):
                    raise DebugCaseConflictError(f"case_id {case_id!r} has different content")
                return persisted
            binding = session.scalar(
                select(DebugCaseRow).where(
                    DebugCaseRow.project_id == project_id,
                    DebugCaseRow.execution_id == case.execution_id,
                )
            )
            if binding is not None:
                raise DebugCaseConflictError(
                    f"execution {case.execution_id!r} already has DebugCase {binding.case_id!r}"
                )
            row = DebugCaseRow(
                case_id=case_id,
                project_id=project_id,
                execution_id=case.execution_id,
                status=case.status,
                category=case.category,
                payload=case.model_dump(mode="json"),
                created_at=case.created_at.replace(tzinfo=None),
                updated_at=case.updated_at.replace(tzinfo=None),
            )
            session.add(row)
            try:
                session.flush()
            except IntegrityError as error:
                raise DebugCaseConflictError("DebugCase identity is already persisted") from error
            return _case_model(row)

    def get_case(self, project_id: str, case_id: str) -> DebugCase:
        with Session(self._engine) as session:
            return _case_model(self._row_for_project(session, project_id, case_id))

    def list_cases(self, project_id: str) -> list[DebugCase]:
        project_id = validate_identifier(project_id)
        with Session(self._engine) as session:
            self._require_project(session, project_id)
            rows = session.scalars(
                select(DebugCaseRow)
                .where(DebugCaseRow.project_id == project_id)
                .order_by(DebugCaseRow.created_at, DebugCaseRow.case_id)
            ).all()
            return [_case_model(row) for row in rows]

    def record_diagnosis(
        self,
        project_id: str,
        case_id: str,
        *,
        hypotheses: list[DiagnosticHypothesis],
        findings: list[DiagnosticFinding],
    ) -> DebugCase:
        with Session(self._engine) as session, session.begin():
            row = self._row_for_project(session, project_id, case_id)
            case = _case_model(row)
            self._require_status(case, {"captured", "diagnosed"})
            updated = case.model_copy(
                update={
                    "status": "diagnosed",
                    "hypotheses": hypotheses,
                    "findings": findings,
                    "updated_at": _utc_now(),
                }
            )
            return _replace_case(row, updated)

    def propose_fix(
        self,
        project_id: str,
        case_id: str,
        proposal: RepairProposal,
    ) -> DebugCase:
        if proposal.case_id != case_id:
            raise DebugCaseRepositoryError("repair proposal case_id does not match DebugCase")
        with Session(self._engine) as session, session.begin():
            row = self._row_for_project(session, project_id, case_id)
            case = _case_model(row)
            self._require_status(case, {"diagnosed"})
            updated = case.model_copy(
                update={"status": "fix_proposed", "proposal": proposal, "updated_at": _utc_now()}
            )
            return _replace_case(row, updated)

    def approve_fix(
        self,
        project_id: str,
        case_id: str,
        *,
        actor_id: str,
        reason: str,
    ) -> DebugCase:
        actor_id = validate_identifier(actor_id)
        if not reason.strip():
            raise ValueError("repair approval reason is required")
        with Session(self._engine) as session, session.begin():
            row = self._row_for_project(session, project_id, case_id)
            case = _case_model(row)
            self._require_status(case, {"fix_proposed"})
            updated = case.model_copy(
                update={
                    "status": "approved",
                    "approved_by": actor_id,
                    "approval_reason": reason.strip(),
                    "updated_at": _utc_now(),
                }
            )
            return _replace_case(row, updated)

    def reject_fix(
        self,
        project_id: str,
        case_id: str,
        *,
        actor_id: str,
        reason: str,
    ) -> DebugCase:
        actor_id = validate_identifier(actor_id)
        if not reason.strip():
            raise ValueError("repair rejection reason is required")
        with Session(self._engine) as session, session.begin():
            row = self._row_for_project(session, project_id, case_id)
            case = _case_model(row)
            self._require_status(case, {"fix_proposed"})
            updated = case.model_copy(
                update={
                    "status": "rejected",
                    "approved_by": actor_id,
                    "approval_reason": reason.strip(),
                    "updated_at": _utc_now(),
                }
            )
            return _replace_case(row, updated)

    def record_regression(
        self,
        project_id: str,
        case_id: str,
        result: RegressionResult,
    ) -> DebugCase:
        with Session(self._engine) as session, session.begin():
            row = self._row_for_project(session, project_id, case_id)
            case = _case_model(row)
            self._require_status(case, {"approved", "regression_failed"})
            updated = case.model_copy(
                update={
                    "status": "regression_passed"
                    if result.status == "passed"
                    else "regression_failed",
                    "regression": result,
                    "updated_at": _utc_now(),
                }
            )
            return _replace_case(row, updated)

    def resolve_case(self, project_id: str, case_id: str, resolution: str) -> DebugCase:
        if not resolution.strip():
            raise ValueError("resolution is required")
        with Session(self._engine) as session, session.begin():
            row = self._row_for_project(session, project_id, case_id)
            case = _case_model(row)
            self._require_status(case, {"regression_passed"})
            updated = case.model_copy(
                update={
                    "status": "resolved",
                    "resolution": resolution.strip(),
                    "updated_at": _utc_now(),
                }
            )
            return _replace_case(row, updated)

    @staticmethod
    def _require_project(session: Session, project_id: str) -> None:
        if session.get(ProjectRow, project_id) is None:
            raise DebugCaseRepositoryError(f"project {project_id!r} was not found")

    @staticmethod
    def _require_status(case: DebugCase, allowed: set[str]) -> None:
        if case.status not in allowed:
            raise DebugCaseRepositoryError(
                f"case {case.case_id!r} cannot transition from status {case.status!r}"
            )

    @staticmethod
    def _row_for_project(session: Session, project_id: str, case_id: str) -> DebugCaseRow:
        project_id = validate_identifier(project_id)
        case_id = validate_identifier(case_id)
        row = session.scalar(
            select(DebugCaseRow).where(
                DebugCaseRow.project_id == project_id,
                DebugCaseRow.case_id == case_id,
            )
        )
        if row is None:
            raise DebugCaseRepositoryError(
                f"DebugCase {case_id!r} was not found in project {project_id!r}"
            )
        return row


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _replace_case(row: DebugCaseRow, case: DebugCase) -> DebugCase:
    row.status = case.status
    row.category = case.category
    row.payload = case.model_dump(mode="json")
    row.updated_at = case.updated_at.replace(tzinfo=None)
    return case


def _case_model(row: DebugCaseRow) -> DebugCase:
    payload = dict(row.payload)
    payload.update(
        {
            "case_id": row.case_id,
            "project_id": row.project_id,
            "execution_id": row.execution_id,
            "status": row.status,
            "category": row.category,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
    )
    return DebugCase.model_validate(payload)
