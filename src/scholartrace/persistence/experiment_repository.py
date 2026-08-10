"""Transactional persistence for frozen experiment plans."""

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
    AlgorithmSpecRow,
    ExperimentPlanRow,
    InnovationCandidateRow,
    ProjectRow,
    utc_now_naive,
)
from scholartrace.schemas import ExperimentPlan


class ExperimentRepositoryError(RuntimeError):
    """Base error for experiment-plan persistence."""


class ExperimentPlanNotFoundError(ExperimentRepositoryError):
    """Raised when a plan is absent from the requested project."""


class ExperimentPlanVersionConflictError(ExperimentRepositoryError):
    """Raised when a plan version would overwrite or skip history."""


class ExperimentPlanDecisionConflictError(ExperimentRepositoryError):
    """Raised when a plan cannot be frozen or rejected safely."""


class ExperimentRepository:
    """Persist draft plans and publish only explicitly frozen versions."""

    def __init__(self, database_path: Path) -> None:
        self._engine = create_sqlite_engine(database_path)

    def close(self) -> None:
        self._engine.dispose()

    def save_plan(self, plan: ExperimentPlan) -> ExperimentPlan:
        if plan.status != "draft":
            raise ValueError("new experiment plans must start as draft")
        project_id = validate_identifier(plan.project_id)
        content_sha256 = experiment_plan_content_sha256(plan)
        if plan.content_sha256 is not None and plan.content_sha256 != content_sha256:
            raise ValueError("experiment plan content_sha256 does not match the canonical payload")
        normalized = plan.model_copy(update={"content_sha256": content_sha256})
        with Session(self._engine) as session, session.begin():
            self._require_project(session, project_id)
            algorithm = session.get(AlgorithmSpecRow, normalized.algorithm_id)
            if algorithm is None or algorithm.project_id != project_id:
                raise ExperimentRepositoryError(
                    f"algorithm {normalized.algorithm_id!r} was not found in project {project_id!r}"
                )
            if algorithm.status != "approved":
                raise ExperimentPlanDecisionConflictError(
                    "experiment plans require an approved algorithm specification"
                )
            self._check_candidate(session, normalized, project_id)
            existing = session.scalar(
                select(ExperimentPlanRow).where(
                    ExperimentPlanRow.project_id == project_id,
                    ExperimentPlanRow.content_sha256 == content_sha256,
                )
            )
            if existing is not None:
                return _plan_model(existing)
            if session.get(ExperimentPlanRow, normalized.plan_id) is not None:
                raise ExperimentPlanVersionConflictError(
                    f"plan_id {normalized.plan_id!r} is already persisted"
                )
            latest = session.scalar(
                select(ExperimentPlanRow)
                .where(ExperimentPlanRow.project_id == project_id)
                .order_by(ExperimentPlanRow.version.desc())
            )
            self._validate_new_version(
                normalized.version,
                normalized.parent_plan_id,
                latest,
            )
            row = ExperimentPlanRow(
                plan_id=normalized.plan_id,
                project_id=project_id,
                algorithm_id=normalized.algorithm_id,
                candidate_id=normalized.candidate_id,
                version=normalized.version,
                content_sha256=content_sha256,
                payload=normalized.model_dump(mode="json"),
                status="draft",
                parent_plan_id=normalized.parent_plan_id,
                created_by=normalized.created_by,
                decision_reason=normalized.decision_reason,
                created_at=normalized.created_at.replace(tzinfo=None),
            )
            session.add(row)
            try:
                session.flush()
            except IntegrityError as error:
                raise ExperimentPlanVersionConflictError(
                    "experiment plan version is already persisted"
                ) from error
            return _plan_model(row)

    def freeze_plan(
        self, project_id: str, plan_id: str, actor_id: str, reason: str
    ) -> ExperimentPlan:
        project_id = validate_identifier(project_id)
        plan_id = validate_identifier(plan_id)
        actor_id = validate_identifier(actor_id)
        if not reason.strip():
            raise ValueError("freeze reason is required")
        with Session(self._engine) as session, session.begin():
            row = self._plan_for_update(session, project_id, plan_id)
            algorithm = session.get(AlgorithmSpecRow, row.algorithm_id)
            if algorithm is None or algorithm.status != "approved":
                raise ExperimentPlanDecisionConflictError(
                    "experiment plans require an approved algorithm specification"
                )
            plan = _plan_model(row)
            self._check_candidate(session, plan, project_id)
            if row.status == "frozen":
                if row.approved_by != actor_id:
                    raise ExperimentPlanDecisionConflictError(
                        "frozen experiment plan belongs to another actor"
                    )
                return plan
            if row.status != "draft":
                raise ExperimentPlanDecisionConflictError(
                    "only draft experiment plans can be frozen"
                )
            siblings = session.scalars(
                select(ExperimentPlanRow).where(
                    ExperimentPlanRow.project_id == project_id,
                    ExperimentPlanRow.status == "frozen",
                    ExperimentPlanRow.version < row.version,
                )
            ).all()
            for sibling in siblings:
                sibling.status = "superseded"
            row.status = "frozen"
            row.approved_by = actor_id
            row.approved_at = utc_now_naive()
            row.decision_reason = reason.strip()
            return _plan_model(row)

    def reject_plan(
        self, project_id: str, plan_id: str, actor_id: str, reason: str
    ) -> ExperimentPlan:
        project_id = validate_identifier(project_id)
        plan_id = validate_identifier(plan_id)
        actor_id = validate_identifier(actor_id)
        if not reason.strip():
            raise ValueError("rejection reason is required")
        with Session(self._engine) as session, session.begin():
            row = self._plan_for_update(session, project_id, plan_id)
            if row.status != "draft":
                raise ExperimentPlanDecisionConflictError(
                    "only draft experiment plans can be rejected"
                )
            row.status = "rejected"
            row.decision_reason = f"{actor_id}: {reason.strip()}"
            return _plan_model(row)

    def get_plan(self, project_id: str, plan_id: str) -> ExperimentPlan:
        project_id = validate_identifier(project_id)
        plan_id = validate_identifier(plan_id)
        with Session(self._engine) as session:
            return _plan_model(self._plan_for_update(session, project_id, plan_id))

    def list_plans(self, project_id: str) -> list[ExperimentPlan]:
        project_id = validate_identifier(project_id)
        with Session(self._engine) as session:
            self._require_project(session, project_id)
            rows = session.scalars(
                select(ExperimentPlanRow)
                .where(ExperimentPlanRow.project_id == project_id)
                .order_by(ExperimentPlanRow.version)
            ).all()
            return [_plan_model(row) for row in rows]

    @staticmethod
    def _require_project(session: Session, project_id: str) -> None:
        if session.get(ProjectRow, project_id) is None:
            raise ExperimentRepositoryError(f"project {project_id!r} was not found")

    @staticmethod
    def _check_candidate(session: Session, plan: ExperimentPlan, project_id: str) -> None:
        if plan.candidate_id is None:
            return
        candidate = session.get(InnovationCandidateRow, plan.candidate_id)
        if candidate is None or candidate.project_id != project_id:
            raise ExperimentPlanDecisionConflictError(
                f"candidate {plan.candidate_id!r} was not found in project {project_id!r}"
            )
        if candidate.algorithm_id != plan.algorithm_id:
            raise ExperimentPlanDecisionConflictError(
                "experiment candidate and algorithm do not match"
            )
        if candidate.status != "approved_for_experiment":
            raise ExperimentPlanDecisionConflictError(
                "experiment plans require a candidate approved for validation"
            )

    @staticmethod
    def _validate_new_version(
        version: int,
        parent_id: str | None,
        latest: ExperimentPlanRow | None,
    ) -> None:
        if latest is None:
            if version != 1 or parent_id is not None:
                raise ExperimentPlanVersionConflictError(
                    "first experiment plan version must be 1 without a parent"
                )
            return
        if version != latest.version + 1:
            raise ExperimentPlanVersionConflictError(
                "experiment plan versions must increment by one"
            )
        if latest.status in {"frozen", "superseded"}:
            if parent_id != latest.plan_id:
                raise ExperimentPlanVersionConflictError(
                    "new experiment plans must name the current frozen parent"
                )
        elif parent_id is not None:
            raise ExperimentPlanVersionConflictError(
                "draft experiment plans cannot be used as a parent"
            )

    @staticmethod
    def _plan_for_update(session: Session, project_id: str, plan_id: str) -> ExperimentPlanRow:
        row = session.scalar(
            select(ExperimentPlanRow).where(
                ExperimentPlanRow.project_id == project_id,
                ExperimentPlanRow.plan_id == plan_id,
            )
        )
        if row is None:
            raise ExperimentPlanNotFoundError(
                f"experiment plan {plan_id!r} was not found in project {project_id!r}"
            )
        return row


def experiment_plan_content_sha256(plan: ExperimentPlan) -> str:
    payload = plan.model_dump(
        mode="json",
        exclude={
            "plan_id",
            "project_id",
            "version",
            "status",
            "content_sha256",
            "parent_plan_id",
            "created_by",
            "decision_reason",
            "approved_by",
            "approved_at",
            "created_at",
        },
    )
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _plan_model(row: ExperimentPlanRow) -> ExperimentPlan:
    payload = dict(row.payload)
    payload.update(
        {
            "plan_id": row.plan_id,
            "project_id": row.project_id,
            "algorithm_id": row.algorithm_id,
            "candidate_id": row.candidate_id,
            "version": row.version,
            "content_sha256": row.content_sha256,
            "status": row.status,
            "parent_plan_id": row.parent_plan_id,
            "created_by": row.created_by,
            "decision_reason": row.decision_reason,
            "approved_by": row.approved_by,
            "approved_at": row.approved_at,
            "created_at": row.created_at,
        }
    )
    return ExperimentPlan.model_validate(payload)
