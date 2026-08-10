"""Persistence and evidence gates for FigureSpec records."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from scholartrace.identifiers import validate_identifier
from scholartrace.persistence.database import create_sqlite_engine
from scholartrace.persistence.models import FigureSpecRow, MetricResultRow, ProjectRow
from scholartrace.schemas import FigureSpec


class FigureRepositoryError(RuntimeError):
    """Base error for figure persistence."""


class FigureConflictError(FigureRepositoryError):
    """Raised when a figure identity or content conflicts."""


class FigureDecisionConflictError(FigureRepositoryError):
    """Raised when a figure is approved or rejected out of order."""


class FigureRepository:
    """Persist draft FigureSpecs and approve only evidence-bound designs."""

    def __init__(self, database_path: Path) -> None:
        self._engine = create_sqlite_engine(database_path)

    def close(self) -> None:
        self._engine.dispose()

    def save_spec(self, spec: FigureSpec) -> FigureSpec:
        if spec.status != "draft":
            raise ValueError("new FigureSpecs must start as draft")
        project_id = validate_identifier(spec.project_id)
        digest = figure_spec_content_sha256(spec)
        if spec.content_sha256 is not None and spec.content_sha256 != digest:
            raise ValueError("figure content_sha256 does not match the canonical payload")
        normalized = spec.model_copy(update={"content_sha256": digest})
        with Session(self._engine) as session, session.begin():
            self._require_project(session, project_id)
            self._validate_metric_references(session, normalized)
            existing_content = session.scalar(
                select(FigureSpecRow).where(
                    FigureSpecRow.project_id == project_id,
                    FigureSpecRow.content_sha256 == digest,
                )
            )
            if existing_content is not None:
                return _figure_model(existing_content)
            if session.get(FigureSpecRow, normalized.figure_id) is not None:
                raise FigureConflictError(
                    f"figure_id {normalized.figure_id!r} is already persisted"
                )
            row = FigureSpecRow(
                figure_id=normalized.figure_id,
                project_id=project_id,
                content_sha256=digest,
                payload=normalized.model_dump(mode="json"),
                status="draft",
                created_by=normalized.created_by,
                created_at=normalized.created_at.replace(tzinfo=None),
            )
            session.add(row)
            try:
                session.flush()
            except IntegrityError as error:
                raise FigureConflictError("figure identity is already persisted") from error
            return _figure_model(row)

    def approve_spec(
        self,
        project_id: str,
        figure_id: str,
        *,
        actor_id: str,
        reason: str,
    ) -> FigureSpec:
        project_id = validate_identifier(project_id)
        figure_id = validate_identifier(figure_id)
        actor_id = validate_identifier(actor_id)
        if not reason.strip():
            raise ValueError("figure approval reason is required")
        with Session(self._engine) as session, session.begin():
            row = self._row_for_project(session, project_id, figure_id)
            if row.status != "draft":
                raise FigureDecisionConflictError("only draft FigureSpecs can be approved")
            spec = _figure_model(row)
            self._validate_metric_references(session, spec)
            normalized = spec.model_copy(update={"status": "approved"})
            row.status = "approved"
            row.payload = normalized.model_dump(mode="json")
            row.payload["approval"] = {"actor_id": actor_id, "reason": reason.strip()}
            return _figure_model(row)

    def reject_spec(
        self,
        project_id: str,
        figure_id: str,
        *,
        actor_id: str,
        reason: str,
    ) -> FigureSpec:
        project_id = validate_identifier(project_id)
        figure_id = validate_identifier(figure_id)
        actor_id = validate_identifier(actor_id)
        if not reason.strip():
            raise ValueError("figure rejection reason is required")
        with Session(self._engine) as session, session.begin():
            row = self._row_for_project(session, project_id, figure_id)
            if row.status != "draft":
                raise FigureDecisionConflictError("only draft FigureSpecs can be rejected")
            spec = _figure_model(row)
            normalized = spec.model_copy(update={"status": "rejected"})
            row.status = "rejected"
            row.payload = normalized.model_dump(mode="json")
            row.payload["rejection"] = {"actor_id": actor_id, "reason": reason.strip()}
            return _figure_model(row)

    def get_spec(self, project_id: str, figure_id: str) -> FigureSpec:
        with Session(self._engine) as session:
            return _figure_model(self._row_for_project(session, project_id, figure_id))

    def list_specs(self, project_id: str) -> list[FigureSpec]:
        project_id = validate_identifier(project_id)
        with Session(self._engine) as session:
            self._require_project(session, project_id)
            rows = session.scalars(
                select(FigureSpecRow)
                .where(FigureSpecRow.project_id == project_id)
                .order_by(FigureSpecRow.created_at, FigureSpecRow.figure_id)
            ).all()
            return [_figure_model(row) for row in rows]

    @staticmethod
    def _require_project(session: Session, project_id: str) -> None:
        if session.get(ProjectRow, project_id) is None:
            raise FigureRepositoryError(f"project {project_id!r} was not found")

    @staticmethod
    def _row_for_project(session: Session, project_id: str, figure_id: str) -> FigureSpecRow:
        project_id = validate_identifier(project_id)
        figure_id = validate_identifier(figure_id)
        row = session.scalar(
            select(FigureSpecRow).where(
                FigureSpecRow.project_id == project_id,
                FigureSpecRow.figure_id == figure_id,
            )
        )
        if row is None:
            raise FigureRepositoryError(
                f"FigureSpec {figure_id!r} was not found in project {project_id!r}"
            )
        return row

    @staticmethod
    def _validate_metric_references(session: Session, spec: FigureSpec) -> None:
        if not spec.metric_result_ids:
            return
        rows = session.scalars(
            select(MetricResultRow).where(
                MetricResultRow.project_id == spec.project_id,
                MetricResultRow.metric_result_id.in_(spec.metric_result_ids),
            )
        ).all()
        if len(rows) != len(set(spec.metric_result_ids)):
            raise FigureRepositoryError("FigureSpec references missing MetricResult records")
        if any(row.verification_status != "verified" or not row.is_final for row in rows):
            raise FigureRepositoryError(
                "FigureSpec can reference only verified final MetricResult records"
            )
        data_versions = {
            str(dict(row.payload).get("data_version"))
            for row in rows
            if dict(row.payload).get("data_version") is not None
        }
        if data_versions and data_versions != {spec.data_version}:
            raise FigureRepositoryError(
                "FigureSpec data_version does not match MetricResult provenance"
            )


def figure_spec_content_sha256(spec: FigureSpec) -> str:
    payload = spec.model_dump(mode="json", exclude={"content_sha256", "status"})
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _figure_model(row: FigureSpecRow) -> FigureSpec:
    payload = dict(row.payload)
    payload.update(
        {
            "figure_id": row.figure_id,
            "project_id": row.project_id,
            "status": row.status,
            "content_sha256": row.content_sha256,
            "created_at": row.created_at,
        }
    )
    payload.pop("approval", None)
    payload.pop("rejection", None)
    return FigureSpec.model_validate(payload)
