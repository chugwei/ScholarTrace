"""Safe import boundaries for existing runs, logs and reported metrics."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from scholartrace.identifiers import validate_identifier
from scholartrace.persistence.database import create_sqlite_engine
from scholartrace.persistence.models import (
    ExperimentPlanRow,
    MetricResultRow,
    ProjectRow,
    RunManifestRow,
)
from scholartrace.schemas import MetricResult, RunManifest

REQUIRED_MANIFEST_FIELDS = (
    "code_sha256",
    "data_version",
    "config_ref",
    "environment_lock",
    "seed",
    "checkpoint_sha256",
    "log_relpath",
    "config_relpath",
    "weights_relpath",
    "metrics_relpath",
)


class RunRepositoryError(RuntimeError):
    """Base error for run and metric imports."""


class RunManifestConflictError(RunRepositoryError):
    """Raised when a run ID is reused with different content."""


class MetricImportConflictError(RunRepositoryError):
    """Raised when a metric identity is reused with different content."""


class RunRepository:
    """Import artifacts without promoting reported values to final metrics."""

    def __init__(self, database_path: Path) -> None:
        self._engine = create_sqlite_engine(database_path)

    def close(self) -> None:
        self._engine.dispose()

    def import_manifest(self, manifest: RunManifest) -> RunManifest:
        project_id = validate_identifier(manifest.project_id)
        with Session(self._engine) as session, session.begin():
            plan = session.get(ExperimentPlanRow, manifest.plan_id)
            if plan is None or plan.project_id != project_id:
                raise RunRepositoryError(
                    f"frozen experiment plan {manifest.plan_id!r} was not found "
                    f"in project {project_id!r}"
                )
            if plan.status != "frozen":
                raise RunRepositoryError("run manifests must reference a frozen experiment plan")
            matrix_ids = {entry["matrix_entry_id"] for entry in plan.payload.get("matrix", [])}
            if manifest.matrix_entry_id not in matrix_ids:
                raise RunRepositoryError(
                    f"matrix entry {manifest.matrix_entry_id!r} is not part of the frozen plan"
                )
            missing = [
                field for field in REQUIRED_MANIFEST_FIELDS if getattr(manifest, field) is None
            ]
            normalized = manifest.model_copy(
                update={
                    "status": "incomplete" if missing else "imported",
                    "missing_requirements": missing,
                }
            )
            existing = session.get(RunManifestRow, normalized.run_id)
            if existing is not None:
                existing_manifest = _manifest_model(existing)
                if existing_manifest.model_dump(exclude={"imported_at"}) != normalized.model_dump(
                    exclude={"imported_at"}
                ):
                    raise RunManifestConflictError(
                        f"run_id {normalized.run_id!r} has different imported content"
                    )
                return existing_manifest
            row = RunManifestRow(
                run_id=normalized.run_id,
                project_id=project_id,
                plan_id=normalized.plan_id,
                matrix_entry_id=normalized.matrix_entry_id,
                status=normalized.status,
                payload=normalized.model_dump(mode="json"),
                created_at=normalized.imported_at.replace(tzinfo=None),
            )
            session.add(row)
            try:
                session.flush()
            except IntegrityError as error:
                raise RunManifestConflictError("run identity is already persisted") from error
            return normalized

    def import_reported_metric(
        self,
        *,
        metric_result_id: str,
        project_id: str,
        run_id: str,
        name: str,
        split: str,
        value: float,
        source: str = "training_log",
        data_version: str | None = None,
    ) -> MetricResult:
        project_id = validate_identifier(project_id)
        metric = MetricResult(
            metric_result_id=metric_result_id,
            project_id=project_id,
            run_id=run_id,
            name=name,
            split=split,
            value=value,
            source=source,
            verification_status="unverifiable",
            is_final=False,
            data_version=data_version,
            created_at=_utc_now(),
        )
        with Session(self._engine) as session, session.begin():
            if session.get(ProjectRow, project_id) is None:
                raise RunRepositoryError(f"project {project_id!r} was not found")
            run = session.get(RunManifestRow, run_id)
            if run is None or run.project_id != project_id:
                raise RunRepositoryError(f"run {run_id!r} was not found in project {project_id!r}")
            existing = session.get(MetricResultRow, metric.metric_result_id)
            if existing is not None:
                persisted = _metric_model(existing)
                if persisted.model_dump(exclude={"created_at"}) != metric.model_dump(
                    exclude={"created_at"}
                ):
                    raise MetricImportConflictError(
                        f"metric_result_id {metric.metric_result_id!r} has different content"
                    )
                return persisted
            row = MetricResultRow(
                metric_result_id=metric.metric_result_id,
                project_id=project_id,
                run_id=run_id,
                name=name,
                split=split,
                value=value,
                source=source,
                verification_status="unverifiable",
                is_final=False,
                payload=metric.model_dump(mode="json"),
                created_at=metric.created_at.replace(tzinfo=None),
            )
            session.add(row)
            try:
                session.flush()
            except IntegrityError as error:
                raise MetricImportConflictError(
                    "reported metric identity is already persisted"
                ) from error
            return metric

    def get_manifest(self, project_id: str, run_id: str) -> RunManifest:
        project_id = validate_identifier(project_id)
        with Session(self._engine) as session:
            row = session.scalar(
                select(RunManifestRow).where(
                    RunManifestRow.project_id == project_id,
                    RunManifestRow.run_id == validate_identifier(run_id),
                )
            )
            if row is None:
                raise RunRepositoryError(f"run {run_id!r} was not found in project {project_id!r}")
            return _manifest_model(row)

    def list_metrics(self, project_id: str, run_id: str | None = None) -> list[MetricResult]:
        project_id = validate_identifier(project_id)
        with Session(self._engine) as session:
            if session.get(ProjectRow, project_id) is None:
                raise RunRepositoryError(f"project {project_id!r} was not found")
            statement = select(MetricResultRow).where(MetricResultRow.project_id == project_id)
            if run_id is not None:
                statement = statement.where(MetricResultRow.run_id == validate_identifier(run_id))
            rows = session.scalars(
                statement.order_by(MetricResultRow.created_at, MetricResultRow.metric_result_id)
            ).all()
            return [_metric_model(row) for row in rows]


def _utc_now():
    from datetime import UTC, datetime

    return datetime.now(UTC)


def _manifest_model(row: RunManifestRow) -> RunManifest:
    payload = dict(row.payload)
    payload.update(
        {
            "run_id": row.run_id,
            "project_id": row.project_id,
            "plan_id": row.plan_id,
            "matrix_entry_id": row.matrix_entry_id,
            "status": row.status,
        }
    )
    return RunManifest.model_validate(payload)


def _metric_model(row: MetricResultRow) -> MetricResult:
    payload = dict(row.payload)
    payload.update(
        {
            "metric_result_id": row.metric_result_id,
            "project_id": row.project_id,
            "run_id": row.run_id,
            "name": row.name,
            "split": row.split,
            "value": row.value,
            "source": row.source,
            "verification_status": row.verification_status,
            "is_final": row.is_final,
            "created_at": row.created_at,
        }
    )
    return MetricResult.model_validate(payload)
