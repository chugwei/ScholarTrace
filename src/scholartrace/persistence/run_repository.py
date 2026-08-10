"""Safe import boundaries for existing runs, logs and reported metrics."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from scholartrace.identifiers import validate_identifier
from scholartrace.persistence.database import create_sqlite_engine
from scholartrace.persistence.models import (
    ClaimUpdateRow,
    ExperimentPlanRow,
    MetricResultRow,
    ProjectRow,
    RunManifestRow,
)
from scholartrace.schemas import ClaimUpdate, MetricAggregate, MetricResult, RunManifest

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

    def record_recomputed_metric(
        self,
        *,
        metric_result_id: str,
        project_id: str,
        run_id: str,
        name: str,
        split: str,
        value: float,
        data_version: str,
        evaluation_script_sha256: str,
    ) -> MetricResult:
        """Record an independently recomputed final metric for a complete Run."""

        project_id = validate_identifier(project_id)
        metric = MetricResult(
            metric_result_id=metric_result_id,
            project_id=project_id,
            run_id=run_id,
            name=name,
            split=split,
            value=value,
            source="independent_recompute",
            verification_status="verified",
            is_final=True,
            data_version=data_version,
            evaluation_script_sha256=evaluation_script_sha256,
            created_at=_utc_now(),
        )
        with Session(self._engine) as session, session.begin():
            run = session.get(RunManifestRow, run_id)
            if run is None or run.project_id != project_id:
                raise RunRepositoryError(f"run {run_id!r} was not found in project {project_id!r}")
            if run.status not in {"imported", "validated"}:
                raise RunRepositoryError(
                    "only complete imported runs can be independently evaluated"
                )
            plan = session.get(ExperimentPlanRow, run.plan_id)
            if plan is None or plan.status != "frozen":
                raise RunRepositoryError("metric recomputation requires a frozen experiment plan")
            if plan.payload.get("data_version") != data_version:
                raise RunRepositoryError(
                    "recomputed metric data_version does not match the frozen plan"
                )
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
                source="independent_recompute",
                verification_status="verified",
                is_final=True,
                payload=metric.model_dump(mode="json"),
                created_at=metric.created_at.replace(tzinfo=None),
            )
            session.add(row)
            run.status = "validated"
            try:
                session.flush()
            except IntegrityError as error:
                raise MetricImportConflictError(
                    "recomputed metric identity is already persisted"
                ) from error
            return metric

    def aggregate_verified_metrics(self, project_id: str, name: str, split: str) -> MetricAggregate:
        project_id = validate_identifier(project_id)
        with Session(self._engine) as session:
            rows = session.scalars(
                select(MetricResultRow).where(
                    MetricResultRow.project_id == project_id,
                    MetricResultRow.name == name,
                    MetricResultRow.split == split,
                    MetricResultRow.verification_status == "verified",
                    MetricResultRow.is_final.is_(True),
                )
            ).all()
            if not rows:
                raise RunRepositoryError("no verified final metrics are available for aggregation")
            values = [row.value for row in rows]
            mean = sum(values) / len(values)
            population_stddev = math.sqrt(
                sum((value - mean) ** 2 for value in values) / len(values)
            )
            return MetricAggregate(
                name=name,
                split=split,
                count=len(rows),
                mean=mean,
                population_stddev=population_stddev,
                metric_result_ids=[row.metric_result_id for row in rows],
            )

    def update_claim(
        self,
        *,
        update_id: str,
        project_id: str,
        claim_id: str,
        status: str,
        metric_result_ids: list[str],
        reason: str,
    ) -> ClaimUpdate:
        project_id = validate_identifier(project_id)
        with Session(self._engine) as session, session.begin():
            rows = [
                row
                for row in session.scalars(
                    select(MetricResultRow).where(
                        MetricResultRow.project_id == project_id,
                        MetricResultRow.metric_result_id.in_(metric_result_ids),
                    )
                ).all()
            ]
            if len(rows) != len(set(metric_result_ids)):
                raise RunRepositoryError("claim update references missing metric results")
            all_verified = bool(rows) and all(
                row.verification_status == "verified" and row.is_final for row in rows
            )
            effective_status = status
            effective_reason = reason
            if status in {"supported", "contradicted"} and not all_verified:
                effective_status = "insufficient"
                effective_reason = f"insufficient verified metrics: {reason}"
            update = ClaimUpdate(
                update_id=update_id,
                project_id=project_id,
                claim_id=claim_id,
                status=effective_status,
                metric_result_ids=metric_result_ids,
                run_ids=sorted({row.run_id for row in rows}),
                reason=effective_reason,
                created_at=_utc_now(),
            )
            existing = session.get(ClaimUpdateRow, update.update_id)
            if existing is not None:
                persisted = _claim_update_model(existing)
                if persisted.model_dump(exclude={"created_at"}) != update.model_dump(
                    exclude={"created_at"}
                ):
                    raise RunRepositoryError(
                        f"update_id {update.update_id!r} has different content"
                    )
                return persisted
            row = ClaimUpdateRow(
                update_id=update.update_id,
                project_id=project_id,
                claim_id=claim_id,
                status=update.status,
                metric_result_ids=update.metric_result_ids,
                run_ids=update.run_ids,
                reason=update.reason,
                payload=update.model_dump(mode="json"),
                created_at=update.created_at.replace(tzinfo=None),
            )
            session.add(row)
            session.flush()
            return update

    def list_claim_updates(self, project_id: str, claim_id: str | None = None) -> list[ClaimUpdate]:
        project_id = validate_identifier(project_id)
        with Session(self._engine) as session:
            statement = select(ClaimUpdateRow).where(ClaimUpdateRow.project_id == project_id)
            if claim_id is not None:
                statement = statement.where(ClaimUpdateRow.claim_id == claim_id)
            rows = session.scalars(
                statement.order_by(ClaimUpdateRow.created_at, ClaimUpdateRow.update_id)
            ).all()
            return [_claim_update_model(row) for row in rows]

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


def _utc_now() -> datetime:
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


def _claim_update_model(row: ClaimUpdateRow) -> ClaimUpdate:
    payload = dict(row.payload)
    payload.update(
        {
            "update_id": row.update_id,
            "project_id": row.project_id,
            "claim_id": row.claim_id,
            "status": row.status,
            "metric_result_ids": row.metric_result_ids,
            "run_ids": row.run_ids,
            "reason": row.reason,
            "created_at": row.created_at,
        }
    )
    return ClaimUpdate.model_validate(payload)
