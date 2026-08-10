"""Transactional persistence for versioned research-design specifications."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from scholartrace.design.validation import DesignValidationError, validate_design_pair
from scholartrace.identifiers import validate_identifier
from scholartrace.persistence.database import create_sqlite_engine
from scholartrace.persistence.models import (
    DataCollectionProtocolRow,
    PipelineSpecRow,
    ProjectRow,
    utc_now_naive,
)
from scholartrace.schemas import DataCollectionProtocol, PipelineSpec


class DesignRepositoryError(RuntimeError):
    """Base error for pipeline and protocol persistence."""


class DesignNotFoundError(DesignRepositoryError):
    """Raised when a design is absent from the requested project."""


class DesignVersionConflictError(DesignRepositoryError):
    """Raised when a design version would overwrite or skip history."""


class DesignDecisionConflictError(DesignRepositoryError):
    """Raised when a design cannot transition through the requested decision."""


class DesignRepository:
    """Persist PipelineSpec and DataCollectionProtocol with explicit version gates."""

    def __init__(self, database_path: Path) -> None:
        self._engine = create_sqlite_engine(database_path)

    def close(self) -> None:
        self._engine.dispose()

    def save_pipeline(self, spec: PipelineSpec) -> PipelineSpec:
        if spec.status != "draft":
            raise ValueError("new pipeline specifications must start as draft")
        project_id = validate_identifier(spec.project_id)
        content_sha256 = pipeline_content_sha256(spec)
        if spec.content_sha256 is not None and spec.content_sha256 != content_sha256:
            raise ValueError("pipeline content_sha256 does not match the canonical payload")
        normalized = spec.model_copy(update={"content_sha256": content_sha256})
        with Session(self._engine) as session, session.begin():
            self._require_project(session, project_id)
            existing = session.scalar(
                select(PipelineSpecRow).where(
                    PipelineSpecRow.project_id == project_id,
                    PipelineSpecRow.content_sha256 == normalized.content_sha256,
                )
            )
            if existing is not None:
                return _pipeline_model(existing)
            identity = session.get(PipelineSpecRow, normalized.pipeline_id)
            if identity is not None:
                raise DesignVersionConflictError(
                    f"pipeline_id {normalized.pipeline_id!r} is already persisted"
                )
            latest = session.scalar(
                select(PipelineSpecRow)
                .where(PipelineSpecRow.project_id == project_id)
                .order_by(PipelineSpecRow.version.desc())
            )
            self._validate_new_version(
                session,
                normalized.version,
                normalized.parent_pipeline_id,
                latest,
                PipelineSpecRow,
                "pipeline",
            )
            row = PipelineSpecRow(
                pipeline_id=normalized.pipeline_id,
                project_id=project_id,
                version=normalized.version,
                content_sha256=normalized.content_sha256,
                payload=normalized.model_dump(mode="json"),
                status="draft",
                parent_pipeline_id=normalized.parent_pipeline_id,
                created_by=normalized.created_by,
                decision_reason=normalized.decision_reason,
                created_at=normalized.created_at.replace(tzinfo=None),
            )
            session.add(row)
            self._flush_or_conflict(session, "pipeline version is already persisted")
            return _pipeline_model(row)

    def save_protocol(self, protocol: DataCollectionProtocol) -> DataCollectionProtocol:
        if protocol.status != "draft":
            raise ValueError("new data-collection protocols must start as draft")
        project_id = validate_identifier(protocol.project_id)
        content_sha256 = protocol_content_sha256(protocol)
        if protocol.content_sha256 is not None and protocol.content_sha256 != content_sha256:
            raise ValueError("protocol content_sha256 does not match the canonical payload")
        normalized = protocol.model_copy(update={"content_sha256": content_sha256})
        with Session(self._engine) as session, session.begin():
            self._require_project(session, project_id)
            existing = session.scalar(
                select(DataCollectionProtocolRow).where(
                    DataCollectionProtocolRow.project_id == project_id,
                    DataCollectionProtocolRow.content_sha256 == normalized.content_sha256,
                )
            )
            if existing is not None:
                return _protocol_model(existing)
            identity = session.get(DataCollectionProtocolRow, normalized.protocol_id)
            if identity is not None:
                raise DesignVersionConflictError(
                    f"protocol_id {normalized.protocol_id!r} is already persisted"
                )
            latest = session.scalar(
                select(DataCollectionProtocolRow)
                .where(DataCollectionProtocolRow.project_id == project_id)
                .order_by(DataCollectionProtocolRow.version.desc())
            )
            self._validate_new_version(
                session,
                normalized.version,
                normalized.parent_protocol_id,
                latest,
                DataCollectionProtocolRow,
                "protocol",
            )
            row = DataCollectionProtocolRow(
                protocol_id=normalized.protocol_id,
                project_id=project_id,
                version=normalized.version,
                content_sha256=normalized.content_sha256,
                payload=normalized.model_dump(mode="json"),
                status="draft",
                parent_protocol_id=normalized.parent_protocol_id,
                created_by=normalized.created_by,
                decision_reason=normalized.decision_reason,
                created_at=normalized.created_at.replace(tzinfo=None),
            )
            session.add(row)
            self._flush_or_conflict(session, "protocol version is already persisted")
            return _protocol_model(row)

    def approve_pipeline(
        self, project_id: str, pipeline_id: str, actor_id: str, reason: str
    ) -> PipelineSpec:
        project_id = validate_identifier(project_id)
        pipeline_id = validate_identifier(pipeline_id)
        actor_id = validate_identifier(actor_id)
        if not reason.strip():
            raise ValueError("approval reason is required")
        with Session(self._engine) as session, session.begin():
            row = self._pipeline_for_update(session, project_id, pipeline_id)
            self._approve_row(session, row, actor_id, reason)
            return _pipeline_model(row)

    def reject_pipeline(
        self, project_id: str, pipeline_id: str, actor_id: str, reason: str
    ) -> PipelineSpec:
        project_id = validate_identifier(project_id)
        pipeline_id = validate_identifier(pipeline_id)
        actor_id = validate_identifier(actor_id)
        if not reason.strip():
            raise ValueError("rejection reason is required")
        with Session(self._engine) as session, session.begin():
            row = self._pipeline_for_update(session, project_id, pipeline_id)
            if row.status != "draft":
                raise DesignDecisionConflictError("only draft pipelines can be rejected")
            row.status = "rejected"
            row.decision_reason = f"{actor_id}: {reason.strip()}"
            session.flush()
            return _pipeline_model(row)

    def approve_protocol(
        self, project_id: str, protocol_id: str, actor_id: str, reason: str
    ) -> DataCollectionProtocol:
        project_id = validate_identifier(project_id)
        protocol_id = validate_identifier(protocol_id)
        actor_id = validate_identifier(actor_id)
        if not reason.strip():
            raise ValueError("approval reason is required")
        with Session(self._engine) as session, session.begin():
            row = self._protocol_for_update(session, project_id, protocol_id)
            self._approve_row(session, row, actor_id, reason)
            return _protocol_model(row)

    def approve_design_pair(
        self,
        project_id: str,
        pipeline_id: str,
        protocol_id: str,
        actor_id: str,
        reason: str,
    ) -> tuple[PipelineSpec, DataCollectionProtocol]:
        """Validate and approve both design documents in one database transaction."""

        project_id = validate_identifier(project_id)
        pipeline_id = validate_identifier(pipeline_id)
        protocol_id = validate_identifier(protocol_id)
        actor_id = validate_identifier(actor_id)
        if not reason.strip():
            raise ValueError("approval reason is required")
        with Session(self._engine) as session, session.begin():
            pipeline_row = self._pipeline_for_update(session, project_id, pipeline_id)
            protocol_row = self._protocol_for_update(session, project_id, protocol_id)
            report = validate_design_pair(
                _pipeline_model(pipeline_row), _protocol_model(protocol_row)
            )
            if not report.passed:
                raise DesignValidationError(report)
            self._approve_row(session, pipeline_row, actor_id, reason)
            self._approve_row(session, protocol_row, actor_id, reason)
            return _pipeline_model(pipeline_row), _protocol_model(protocol_row)

    def reject_protocol(
        self, project_id: str, protocol_id: str, actor_id: str, reason: str
    ) -> DataCollectionProtocol:
        project_id = validate_identifier(project_id)
        protocol_id = validate_identifier(protocol_id)
        actor_id = validate_identifier(actor_id)
        if not reason.strip():
            raise ValueError("rejection reason is required")
        with Session(self._engine) as session, session.begin():
            row = self._protocol_for_update(session, project_id, protocol_id)
            if row.status != "draft":
                raise DesignDecisionConflictError("only draft protocols can be rejected")
            row.status = "rejected"
            row.decision_reason = f"{actor_id}: {reason.strip()}"
            session.flush()
            return _protocol_model(row)

    def get_pipeline(self, project_id: str, pipeline_id: str) -> PipelineSpec:
        project_id = validate_identifier(project_id)
        pipeline_id = validate_identifier(pipeline_id)
        with Session(self._engine) as session:
            return _pipeline_model(self._pipeline_for_update(session, project_id, pipeline_id))

    def get_protocol(self, project_id: str, protocol_id: str) -> DataCollectionProtocol:
        project_id = validate_identifier(project_id)
        protocol_id = validate_identifier(protocol_id)
        with Session(self._engine) as session:
            return _protocol_model(self._protocol_for_update(session, project_id, protocol_id))

    def list_pipelines(self, project_id: str) -> list[PipelineSpec]:
        project_id = validate_identifier(project_id)
        with Session(self._engine) as session:
            self._require_project(session, project_id)
            rows = session.scalars(
                select(PipelineSpecRow)
                .where(PipelineSpecRow.project_id == project_id)
                .order_by(PipelineSpecRow.version)
            ).all()
            return [_pipeline_model(row) for row in rows]

    def list_protocols(self, project_id: str) -> list[DataCollectionProtocol]:
        project_id = validate_identifier(project_id)
        with Session(self._engine) as session:
            self._require_project(session, project_id)
            rows = session.scalars(
                select(DataCollectionProtocolRow)
                .where(DataCollectionProtocolRow.project_id == project_id)
                .order_by(DataCollectionProtocolRow.version)
            ).all()
            return [_protocol_model(row) for row in rows]

    @staticmethod
    def _require_project(session: Session, project_id: str) -> None:
        if session.get(ProjectRow, project_id) is None:
            raise DesignRepositoryError(f"project {project_id!r} was not found")

    @staticmethod
    def _validate_new_version(
        session: Session,
        version: int,
        parent_id: str | None,
        latest: PipelineSpecRow | DataCollectionProtocolRow | None,
        row_type: type[PipelineSpecRow] | type[DataCollectionProtocolRow],
        label: str,
    ) -> None:
        if latest is None:
            if version != 1 or parent_id is not None:
                raise DesignVersionConflictError(
                    f"first {label} version must be 1 without a parent"
                )
            return
        latest_version = latest.version
        if version != latest_version + 1:
            raise DesignVersionConflictError(f"{label} versions must increment by one")
        latest_id = (
            latest.pipeline_id if isinstance(latest, PipelineSpecRow) else latest.protocol_id
        )
        if latest.status in {"approved", "superseded"}:
            if parent_id != latest_id:
                raise DesignVersionConflictError(
                    f"new {label} versions must name the current approved parent"
                )
        elif parent_id is not None:
            parent = session.get(row_type, parent_id)
            if parent is None or parent.status not in {"approved", "superseded"}:
                raise DesignVersionConflictError(f"{label} parent must be an approved version")

    @staticmethod
    def _flush_or_conflict(session: Session, message: str) -> None:
        try:
            session.flush()
        except IntegrityError as error:
            raise DesignVersionConflictError(message) from error

    @staticmethod
    def _approve_row(
        session: Session,
        row: PipelineSpecRow | DataCollectionProtocolRow,
        actor_id: str,
        reason: str,
    ) -> None:
        if row.status == "approved":
            if row.approved_by != actor_id:
                raise DesignDecisionConflictError("approved design belongs to another actor")
            return
        if row.status != "draft":
            raise DesignDecisionConflictError("only draft designs can be approved")
        if isinstance(row, PipelineSpecRow):
            siblings = PipelineSpecRow
        else:
            siblings = DataCollectionProtocolRow
        project_id = row.project_id
        version = row.version
        for sibling in session.scalars(
            select(siblings).where(
                siblings.project_id == project_id,
                siblings.status == "approved",
                siblings.version < version,
            )
        ).all():
            sibling.status = "superseded"
        row.status = "approved"
        row.approved_by = actor_id
        row.approved_at = utc_now_naive()
        row.decision_reason = reason.strip()

    @staticmethod
    def _pipeline_for_update(
        session: Session, project_id: str, pipeline_id: str
    ) -> PipelineSpecRow:
        row = session.scalar(
            select(PipelineSpecRow).where(
                PipelineSpecRow.project_id == project_id,
                PipelineSpecRow.pipeline_id == pipeline_id,
            )
        )
        if row is None:
            raise DesignNotFoundError(
                f"pipeline {pipeline_id!r} was not found in project {project_id!r}"
            )
        return row

    @staticmethod
    def _protocol_for_update(
        session: Session, project_id: str, protocol_id: str
    ) -> DataCollectionProtocolRow:
        row = session.scalar(
            select(DataCollectionProtocolRow).where(
                DataCollectionProtocolRow.project_id == project_id,
                DataCollectionProtocolRow.protocol_id == protocol_id,
            )
        )
        if row is None:
            raise DesignNotFoundError(
                f"protocol {protocol_id!r} was not found in project {project_id!r}"
            )
        return row


def pipeline_content_sha256(spec: PipelineSpec) -> str:
    return _content_sha256(
        spec.model_dump(
            mode="json",
            exclude={
                "pipeline_id",
                "project_id",
                "version",
                "status",
                "content_sha256",
                "parent_pipeline_id",
                "created_by",
                "decision_reason",
                "approved_by",
                "approved_at",
                "created_at",
            },
        )
    )


def protocol_content_sha256(protocol: DataCollectionProtocol) -> str:
    return _content_sha256(
        protocol.model_dump(
            mode="json",
            exclude={
                "protocol_id",
                "project_id",
                "version",
                "status",
                "content_sha256",
                "parent_protocol_id",
                "created_by",
                "decision_reason",
                "approved_by",
                "approved_at",
                "created_at",
            },
        )
    )


def _content_sha256(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _pipeline_model(row: PipelineSpecRow) -> PipelineSpec:
    payload = dict(row.payload)
    payload.update(
        {
            "pipeline_id": row.pipeline_id,
            "project_id": row.project_id,
            "version": row.version,
            "content_sha256": row.content_sha256,
            "status": row.status,
            "parent_pipeline_id": row.parent_pipeline_id,
            "created_by": row.created_by,
            "decision_reason": row.decision_reason,
            "approved_by": row.approved_by,
            "approved_at": row.approved_at,
            "created_at": row.created_at,
        }
    )
    return PipelineSpec.model_validate(payload)


def _protocol_model(row: DataCollectionProtocolRow) -> DataCollectionProtocol:
    payload = dict(row.payload)
    payload.update(
        {
            "protocol_id": row.protocol_id,
            "project_id": row.project_id,
            "version": row.version,
            "content_sha256": row.content_sha256,
            "status": row.status,
            "parent_protocol_id": row.parent_protocol_id,
            "created_by": row.created_by,
            "decision_reason": row.decision_reason,
            "approved_by": row.approved_by,
            "approved_at": row.approved_at,
            "created_at": row.created_at,
        }
    )
    return DataCollectionProtocol.model_validate(payload)
