from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from scholartrace.persistence.database import create_sqlite_engine
from scholartrace.persistence.figure_repository import (
    FigureDecisionConflictError,
    FigureRepository,
    FigureRepositoryError,
)
from scholartrace.persistence.migrations import (
    LATEST_REVISION,
    current_revision,
    downgrade_database,
    upgrade_database,
)
from scholartrace.persistence.models import (
    AlgorithmSpecRow,
    ExperimentPlanRow,
    MetricResultRow,
    RunManifestRow,
)
from scholartrace.persistence.repository import ProjectRepository
from scholartrace.schemas import FigurePoint, FigureSpec

CREATED_AT = datetime(2026, 8, 11, tzinfo=UTC)


def setup_database(database_path: Path, *, verified: bool = True) -> None:
    upgrade_database(database_path)
    project = ProjectRepository(database_path)
    project.create_project("lychee-m9", "lychee-m9")
    project.close()
    engine = create_sqlite_engine(database_path)
    with Session(engine) as session, session.begin():
        session.add(
            AlgorithmSpecRow(
                algorithm_id="algo-m9",
                project_id="lychee-m9",
                version=1,
                content_sha256="a" * 64,
                payload={},
                status="approved",
                created_by="researcher-001",
                created_at=CREATED_AT.replace(tzinfo=None),
            )
        )
        session.flush()
        session.add(
            ExperimentPlanRow(
                plan_id="plan-m9",
                project_id="lychee-m9",
                algorithm_id="algo-m9",
                version=1,
                content_sha256="b" * 64,
                payload={"matrix": [], "data_version": "sha256:data-v1"},
                status="frozen",
                created_by="researcher-001",
                created_at=CREATED_AT.replace(tzinfo=None),
            )
        )
        session.flush()
        session.add(
            RunManifestRow(
                run_id="run-m9",
                project_id="lychee-m9",
                plan_id="plan-m9",
                matrix_entry_id="matrix-m9",
                status="validated",
                payload={},
                created_at=CREATED_AT.replace(tzinfo=None),
            )
        )
        session.flush()
        session.add(
            MetricResultRow(
                metric_result_id="metric-m9",
                project_id="lychee-m9",
                run_id="run-m9",
                name="accuracy",
                split="validation",
                value=0.9,
                source="independent_recompute",
                verification_status="verified" if verified else "unverifiable",
                is_final=verified,
                payload={"data_version": "sha256:data-v1"},
                created_at=CREATED_AT.replace(tzinfo=None),
            )
        )
    engine.dispose()


def spec(*, figure_id: str = "figure-m9") -> FigureSpec:
    return FigureSpec(
        figure_id=figure_id,
        project_id="lychee-m9",
        title="Validation accuracy",
        kind="bar",
        x_label="method",
        y_label="accuracy",
        points=[FigurePoint(label="proposed", value=0.9, metric_result_id="metric-m9")],
        metric_result_ids=["metric-m9"],
        data_version="sha256:data-v1",
        caption="Validation accuracy from the verified metric result.",
        created_by="researcher-001",
        created_at=CREATED_AT,
    )


def test_figure_migration_rolls_back(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    assert current_revision(database_path) == LATEST_REVISION
    downgrade_database(database_path, "0016")
    assert current_revision(database_path) == "0016"
    upgrade_database(database_path)
    assert current_revision(database_path) == LATEST_REVISION


def test_figure_spec_requires_verified_metric_and_approval(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    setup_database(database_path)
    repository = FigureRepository(database_path)
    saved = repository.save_spec(spec())
    assert saved.status == "draft"
    assert len(saved.content_sha256 or "") == 64
    assert repository.save_spec(spec()) == saved
    approved = repository.approve_spec(
        "lychee-m9",
        "figure-m9",
        actor_id="researcher-001",
        reason="verified metric and explicit caption",
    )
    assert approved.status == "approved"
    with pytest.raises(FigureDecisionConflictError, match="only draft"):
        repository.approve_spec(
            "lychee-m9",
            "figure-m9",
            actor_id="researcher-001",
            reason="duplicate approval",
        )
    repository.close()


def test_figure_rejects_unverified_and_mismatched_metric_data(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    setup_database(database_path, verified=False)
    repository = FigureRepository(database_path)
    with pytest.raises(FigureRepositoryError, match="verified final"):
        repository.save_spec(spec())
    repository.close()

    other_database = tmp_path / "other.db"
    setup_database(other_database)
    repository = FigureRepository(other_database)
    with pytest.raises(FigureRepositoryError, match="data_version"):
        repository.save_spec(spec().model_copy(update={"data_version": "sha256:wrong"}))
    repository.close()
