"""Transactional repository for projects and research questions."""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from scholartrace.identifiers import validate_identifier
from scholartrace.persistence.database import create_sqlite_engine
from scholartrace.persistence.models import (
    DecisionRecordRow,
    ProjectRow,
    ResearchQuestionRow,
    utc_now_naive,
)
from scholartrace.schemas import ResearchQuestion
from scholartrace.schemas.decisions import DecisionRecord


class ProjectRepositoryError(RuntimeError):
    """Base error for repository operations."""


class ProjectNotFoundError(ProjectRepositoryError):
    """Raised when a project-scoped operation cannot find its project."""


class ProjectIdentityConflictError(ProjectRepositoryError):
    """Raised when a project or thread identifier is already bound differently."""


class ResearchQuestionNotFoundError(ProjectRepositoryError):
    """Raised when a research question is not present in the requested project."""


class ResearchQuestionFrozenError(ProjectRepositoryError):
    """Raised when a frozen question is changed without creating a new version."""


class ResearchQuestionVersionConflictError(ProjectRepositoryError):
    """Raised when a new version does not descend from the current frozen version."""


class ResearchQuestionConcurrentUpdateError(ProjectRepositoryError):
    """Raised when concurrent writes race on the next research question version.

    The version slot is a read-then-write over ``max(version)``; two concurrent
    saves can compute the same next version and trip the
    ``(project_id, version)`` unique constraint. Callers may retry the request.
    """


class DecisionConflictError(ProjectRepositoryError):
    """Raised when a decision ID is replayed with different content."""


@dataclass(frozen=True, slots=True)
class ProjectRecord:
    project_id: str
    thread_id: str
    active_stage: str
    current_goal: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ResearchQuestionRecord:
    research_question_id: str
    project_id: str
    version: int
    content_sha256: str
    question: ResearchQuestion
    status: Literal["draft", "frozen"]
    frozen_at: datetime | None
    frozen_by: str | None
    parent_research_question_id: str | None
    created_at: datetime


class ProjectRepository:
    """Persist M1 project entities in short, atomic SQLAlchemy sessions."""

    def __init__(self, database_path: Path) -> None:
        self._engine = create_sqlite_engine(database_path)

    def close(self) -> None:
        self._engine.dispose()

    def create_project(
        self,
        project_id: str,
        thread_id: str,
        current_goal: str | None = None,
    ) -> ProjectRecord:
        project_id = validate_identifier(project_id)
        thread_id = validate_identifier(thread_id)
        try:
            with Session(self._engine) as session, session.begin():
                existing = session.get(ProjectRow, project_id)
                if existing is not None:
                    if existing.thread_id != thread_id or existing.current_goal != current_goal:
                        raise ProjectIdentityConflictError(
                            f"project_id {project_id!r} already has different identity fields"
                        )
                    return _project_record(existing)

                thread_owner = session.scalar(
                    select(ProjectRow).where(ProjectRow.thread_id == thread_id)
                )
                if thread_owner is not None:
                    raise ProjectIdentityConflictError(
                        f"thread_id {thread_id!r} is already assigned to another project"
                    )

                row = ProjectRow(
                    project_id=project_id,
                    thread_id=thread_id,
                    active_stage="intake",
                    current_goal=current_goal,
                )
                session.add(row)
                session.flush()
                return _project_record(row)
        except IntegrityError as error:
            raise ProjectIdentityConflictError(
                "project_id or thread_id is already assigned"
            ) from error

    def get_project(self, project_id: str) -> ProjectRecord:
        project_id = validate_identifier(project_id)
        with Session(self._engine) as session:
            row = session.get(ProjectRow, project_id)
            if row is None:
                raise ProjectNotFoundError(f"project {project_id!r} was not found")
            return _project_record(row)

    def list_projects(self) -> list[ProjectRecord]:
        with Session(self._engine) as session:
            rows = session.scalars(select(ProjectRow).order_by(ProjectRow.project_id)).all()
            return [_project_record(row) for row in rows]

    def update_project_stage(self, project_id: str, active_stage: str) -> ProjectRecord:
        """Update the durable workflow stage without changing project identity."""

        project_id = validate_identifier(project_id)
        active_stage = validate_identifier(active_stage)
        with Session(self._engine) as session, session.begin():
            project = session.get(ProjectRow, project_id)
            if project is None:
                raise ProjectNotFoundError(f"project {project_id!r} was not found")
            project.active_stage = active_stage
            session.flush()
            return _project_record(project)

    def save_research_question(
        self,
        project_id: str,
        question: ResearchQuestion,
        active_stage: str | None = None,
        parent_research_question_id: str | None = None,
    ) -> ResearchQuestionRecord:
        project_id = validate_identifier(project_id)
        if active_stage is not None:
            active_stage = validate_identifier(active_stage)
        if parent_research_question_id is not None:
            parent_research_question_id = validate_identifier(parent_research_question_id)
        payload = question.model_dump(mode="json")
        content_sha256 = _research_question_content_sha256(payload)
        research_question_id = research_question_id_for(project_id, question)

        with Session(self._engine) as session, session.begin():
            project = session.get(ProjectRow, project_id)
            if project is None:
                raise ProjectNotFoundError(f"project {project_id!r} was not found")

            existing = session.scalar(
                select(ResearchQuestionRow).where(
                    ResearchQuestionRow.project_id == project_id,
                    ResearchQuestionRow.content_sha256 == content_sha256,
                )
            )
            if existing is not None:
                if active_stage is not None:
                    project.active_stage = active_stage
                session.flush()
                return _research_question_record(existing)

            latest = session.scalar(
                select(ResearchQuestionRow)
                .where(ResearchQuestionRow.project_id == project_id)
                .order_by(ResearchQuestionRow.version.desc())
            )
            parent = None
            if parent_research_question_id is not None:
                parent = session.scalar(
                    select(ResearchQuestionRow).where(
                        ResearchQuestionRow.project_id == project_id,
                        ResearchQuestionRow.research_question_id == parent_research_question_id,
                    )
                )
                if parent is None:
                    raise ResearchQuestionNotFoundError(
                        f"research question {parent_research_question_id!r} was not found in "
                        f"project {project_id!r}"
                    )
                if parent.status != "frozen":
                    raise ResearchQuestionVersionConflictError(
                        "new versions must descend from a frozen research question"
                    )
                if (
                    latest is not None
                    and latest.research_question_id != parent.research_question_id
                ):
                    raise ResearchQuestionVersionConflictError(
                        "new version parent must be the current research question"
                    )
            elif latest is not None and latest.status == "frozen":
                raise ResearchQuestionFrozenError(
                    "research question is frozen; create a new version explicitly"
                )
            if active_stage is not None:
                project.active_stage = active_stage

            latest_version = session.scalar(
                select(func.max(ResearchQuestionRow.version)).where(
                    ResearchQuestionRow.project_id == project_id
                )
            )
            row = ResearchQuestionRow(
                research_question_id=research_question_id,
                project_id=project_id,
                version=(latest_version or 0) + 1,
                content_sha256=content_sha256,
                payload=payload,
                status="draft",
                parent_research_question_id=parent_research_question_id,
            )
            session.add(row)
            try:
                session.flush()
            except IntegrityError as error:
                # Concurrent saves race on the (project_id, version) unique
                # constraint because the next version is a read-then-write.
                # Surface it as a retriable conflict rather than a 500.
                raise ResearchQuestionConcurrentUpdateError(
                    "research question version conflicted with a concurrent save; retry the request"
                ) from error
            return _research_question_record(row)

    def create_research_question_version(
        self,
        project_id: str,
        parent_research_question_id: str,
        question: ResearchQuestion,
        active_stage: str | None = None,
    ) -> ResearchQuestionRecord:
        """Create a draft descendant of the project's current frozen question."""

        return self.save_research_question(
            project_id,
            question,
            active_stage=active_stage,
            parent_research_question_id=parent_research_question_id,
        )

    def freeze_research_question(
        self,
        project_id: str,
        research_question_id: str,
        frozen_by: str,
    ) -> ResearchQuestionRecord:
        """Freeze one draft version idempotently and bind the approving actor."""

        project_id = validate_identifier(project_id)
        research_question_id = validate_identifier(research_question_id)
        frozen_by = validate_identifier(frozen_by)
        with Session(self._engine) as session, session.begin():
            project = session.get(ProjectRow, project_id)
            if project is None:
                raise ProjectNotFoundError(f"project {project_id!r} was not found")
            row = session.scalar(
                select(ResearchQuestionRow).where(
                    ResearchQuestionRow.project_id == project_id,
                    ResearchQuestionRow.research_question_id == research_question_id,
                )
            )
            if row is None:
                raise ResearchQuestionNotFoundError(
                    f"research question {research_question_id!r} was not found in "
                    f"project {project_id!r}"
                )
            if row.status == "frozen":
                if row.frozen_by != frozen_by:
                    raise ResearchQuestionFrozenError(
                        f"research question {research_question_id!r} is already frozen"
                    )
                return _research_question_record(row)
            latest = session.scalar(
                select(ResearchQuestionRow)
                .where(ResearchQuestionRow.project_id == project_id)
                .order_by(ResearchQuestionRow.version.desc())
            )
            if latest is not None and latest.research_question_id != row.research_question_id:
                raise ResearchQuestionVersionConflictError(
                    "only the current research question can be frozen"
                )
            row.status = "frozen"
            row.frozen_at = utc_now_naive()
            row.frozen_by = frozen_by
            project.active_stage = "completed"
            session.flush()
            return _research_question_record(row)

    def get_research_question(
        self,
        project_id: str,
        research_question_id: str,
    ) -> ResearchQuestionRecord:
        project_id = validate_identifier(project_id)
        research_question_id = validate_identifier(research_question_id)
        with Session(self._engine) as session:
            row = session.scalar(
                select(ResearchQuestionRow).where(
                    ResearchQuestionRow.project_id == project_id,
                    ResearchQuestionRow.research_question_id == research_question_id,
                )
            )
            if row is None:
                raise ResearchQuestionNotFoundError(
                    f"research question {research_question_id!r} was not found in "
                    f"project {project_id!r}"
                )
            return _research_question_record(row)

    def list_research_questions(self, project_id: str) -> list[ResearchQuestionRecord]:
        project_id = validate_identifier(project_id)
        with Session(self._engine) as session:
            if session.get(ProjectRow, project_id) is None:
                raise ProjectNotFoundError(f"project {project_id!r} was not found")
            rows = session.scalars(
                select(ResearchQuestionRow)
                .where(ResearchQuestionRow.project_id == project_id)
                .order_by(ResearchQuestionRow.version)
            ).all()
            return [_research_question_record(row) for row in rows]

    def record_decision(
        self,
        decision_id: str,
        project_id: str,
        thread_id: str,
        target_type: str,
        target_id: str,
        action: str,
        actor_id: str,
        reason: str | None = None,
        payload: dict[str, object] | None = None,
        created_at: datetime | str | None = None,
    ) -> DecisionRecord:
        project_id = validate_identifier(project_id)
        thread_id = validate_identifier(thread_id)
        target_id = validate_identifier(target_id)
        record = DecisionRecord.model_validate(
            {
                "decision_id": decision_id,
                "project_id": project_id,
                "thread_id": thread_id,
                "target_type": target_type,
                "target_id": target_id,
                "action": action,
                "actor_id": actor_id,
                "reason": reason,
                "payload": payload or {},
                "created_at": created_at or utc_now_naive(),
            }
        )
        with Session(self._engine) as session, session.begin():
            project = session.get(ProjectRow, project_id)
            if project is None:
                raise ProjectNotFoundError(f"project {project_id!r} was not found")
            if project.thread_id != thread_id:
                raise ProjectIdentityConflictError(
                    f"thread_id {thread_id!r} is not assigned to project {project_id!r}"
                )
            existing = session.get(DecisionRecordRow, record.decision_id)
            if existing is not None:
                existing_record = _decision_record(existing)
                if _same_decision_except_time(existing_record, record):
                    return existing_record
                raise DecisionConflictError(
                    f"decision_id {record.decision_id!r} already has different content"
                )
            row = DecisionRecordRow(
                decision_id=record.decision_id,
                project_id=record.project_id,
                thread_id=record.thread_id,
                target_type=record.target_type,
                target_id=record.target_id,
                action=record.action,
                actor_id=record.actor_id,
                reason=record.reason,
                payload=record.payload,
                created_at=record.created_at.replace(tzinfo=None),
            )
            session.add(row)
            session.flush()
            return _decision_record(row)

    def list_decisions(
        self,
        project_id: str,
        *,
        target_type: str | None = None,
        action: str | None = None,
    ) -> list[DecisionRecord]:
        project_id = validate_identifier(project_id)
        with Session(self._engine) as session:
            if session.get(ProjectRow, project_id) is None:
                raise ProjectNotFoundError(f"project {project_id!r} was not found")
            statement = select(DecisionRecordRow).where(DecisionRecordRow.project_id == project_id)
            if target_type is not None:
                statement = statement.where(DecisionRecordRow.target_type == target_type)
            if action is not None:
                statement = statement.where(DecisionRecordRow.action == action)
            rows = session.scalars(
                statement.order_by(DecisionRecordRow.created_at, DecisionRecordRow.decision_id)
            ).all()
            return [_decision_record(row) for row in rows]

    def list_audit_records(self, project_id: str) -> list[DecisionRecord]:
        """Return all human and checkpoint audit records in chronological order."""

        return self.list_decisions(project_id)


def _project_record(row: ProjectRow) -> ProjectRecord:
    return ProjectRecord(
        project_id=row.project_id,
        thread_id=row.thread_id,
        active_stage=row.active_stage,
        current_goal=row.current_goal,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _research_question_record(row: ResearchQuestionRow) -> ResearchQuestionRecord:
    return ResearchQuestionRecord(
        research_question_id=row.research_question_id,
        project_id=row.project_id,
        version=row.version,
        content_sha256=row.content_sha256,
        question=ResearchQuestion.model_validate(row.payload),
        status=row.status,
        frozen_at=row.frozen_at,
        frozen_by=row.frozen_by,
        parent_research_question_id=row.parent_research_question_id,
        created_at=row.created_at,
    )


def research_question_id_for(project_id: str, question: ResearchQuestion) -> str:
    """Return the stable ID used for a project's canonical question payload."""

    project_id = validate_identifier(project_id)
    content_sha256 = _research_question_content_sha256(question.model_dump(mode="json"))
    identity_digest = hashlib.sha256(f"{project_id}\0{content_sha256}".encode()).hexdigest()
    return f"rq_{identity_digest[:32]}"


def _research_question_content_sha256(payload: dict[str, object]) -> str:
    canonical_payload = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()


def _decision_record(row: DecisionRecordRow) -> DecisionRecord:
    return DecisionRecord.model_validate(
        {
            "decision_id": row.decision_id,
            "project_id": row.project_id,
            "thread_id": row.thread_id,
            "target_type": row.target_type,
            "target_id": row.target_id,
            "action": row.action,
            "actor_id": row.actor_id,
            "reason": row.reason,
            "payload": row.payload,
            "created_at": row.created_at,
        }
    )


def _same_decision_except_time(left: DecisionRecord, right: DecisionRecord) -> bool:
    return left.model_dump(exclude={"created_at"}) == right.model_dump(exclude={"created_at"})
