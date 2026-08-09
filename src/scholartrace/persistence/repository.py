"""Transactional repository for projects and research questions."""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from scholartrace.identifiers import validate_identifier
from scholartrace.persistence.database import create_sqlite_engine
from scholartrace.persistence.models import ProjectRow, ResearchQuestionRow
from scholartrace.schemas import ResearchQuestion


class ProjectRepositoryError(RuntimeError):
    """Base error for repository operations."""


class ProjectNotFoundError(ProjectRepositoryError):
    """Raised when a project-scoped operation cannot find its project."""


class ProjectIdentityConflictError(ProjectRepositoryError):
    """Raised when a project or thread identifier is already bound differently."""


class ResearchQuestionNotFoundError(ProjectRepositoryError):
    """Raised when a research question is not present in the requested project."""


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

    def save_research_question(
        self,
        project_id: str,
        question: ResearchQuestion,
    ) -> ResearchQuestionRecord:
        project_id = validate_identifier(project_id)
        payload = question.model_dump(mode="json")
        canonical_payload = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        content_sha256 = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
        identity_digest = hashlib.sha256(f"{project_id}\0{content_sha256}".encode()).hexdigest()
        research_question_id = f"rq_{identity_digest[:32]}"

        with Session(self._engine) as session, session.begin():
            if session.get(ProjectRow, project_id) is None:
                raise ProjectNotFoundError(f"project {project_id!r} was not found")

            existing = session.scalar(
                select(ResearchQuestionRow).where(
                    ResearchQuestionRow.project_id == project_id,
                    ResearchQuestionRow.content_sha256 == content_sha256,
                )
            )
            if existing is not None:
                return _research_question_record(existing)

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
            )
            session.add(row)
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
        created_at=row.created_at,
    )
