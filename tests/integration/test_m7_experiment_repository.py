from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from scholartrace.persistence.database import create_sqlite_engine
from scholartrace.persistence.experiment_repository import (
    ExperimentPlanDecisionConflictError,
    ExperimentPlanVersionConflictError,
    ExperimentRepository,
)
from scholartrace.persistence.migrations import (
    LATEST_REVISION,
    current_revision,
    downgrade_database,
    upgrade_database,
)
from scholartrace.persistence.models import AlgorithmSpecRow
from scholartrace.persistence.repository import ProjectRepository
from scholartrace.schemas import ExperimentMatrixEntry, ExperimentPlan

CREATED_AT = datetime(2026, 8, 11, tzinfo=UTC)


def create_project(database_path: Path, project_id: str = "lychee-m7") -> None:
    repository = ProjectRepository(database_path)
    repository.create_project(project_id, project_id)
    repository.close()


def add_algorithm(
    database_path: Path,
    project_id: str = "lychee-m7",
    algorithm_id: str = "algo-m7",
    status: str = "approved",
) -> None:
    engine = create_sqlite_engine(database_path)
    with Session(engine) as session, session.begin():
        session.add(
            AlgorithmSpecRow(
                algorithm_id=algorithm_id,
                project_id=project_id,
                version=1,
                content_sha256="a" * 64,
                payload={},
                status=status,
                created_by="researcher-001",
                created_at=CREATED_AT.replace(tzinfo=None),
            )
        )
    engine.dispose()


def plan(
    *, version: int = 1, parent: str | None = None, objective: str = "Test mechanism"
) -> ExperimentPlan:
    return ExperimentPlan(
        plan_id=f"plan-v{version}",
        project_id="lychee-m7",
        algorithm_id="algo-m7",
        version=version,
        objective=objective,
        hypotheses=["visibility supervision changes held-out recall"],
        datasets=["lychee-fixture-v1"],
        baselines=["standard detector"],
        proposed_methods=["visibility-aware detector"],
        independent_variables=["visibility head"],
        controlled_variables=["threshold and split"],
        metrics=["recall", "mae"],
        statistical_tests=["paired bootstrap"],
        seeds=[7, 11],
        repeats=2,
        ablations=["without visibility head"],
        resource_budget={"cpu_hours": 2, "gpu_hours": 1},
        stopping_criteria=["stop after two failed reproducibility checks"],
        expected_artifacts=["run manifest", "metric report"],
        failure_and_fallback_plan=["mark incomplete when a required artifact is missing"],
        matrix=[
            ExperimentMatrixEntry(
                matrix_entry_id="matrix-baseline",
                name="baseline",
                method_kind="baseline",
                method_ref="standard detector",
                dataset_version="lychee-fixture-v1",
                config_ref="configs/baseline.yaml",
                seeds=[7, 11],
                repeats=2,
                metrics=["recall", "mae"],
            ),
            ExperimentMatrixEntry(
                matrix_entry_id="matrix-proposed",
                name="proposed",
                method_kind="proposed",
                method_ref="visibility-aware detector",
                dataset_version="lychee-fixture-v1",
                config_ref="configs/proposed.yaml",
                seeds=[7, 11],
                repeats=2,
                metrics=["recall", "mae"],
            ),
        ],
        data_version="sha256:fixture-v1",
        code_sha256="b" * 64,
        environment_lock="uv.lock@fixture",
        config_refs=["configs/baseline.yaml", "configs/proposed.yaml"],
        parent_plan_id=parent,
        created_by="researcher-001",
        created_at=CREATED_AT,
    )


def test_m7_plan_migration_rolls_back(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    assert current_revision(database_path) == LATEST_REVISION
    downgrade_database(database_path, "0010")
    assert current_revision(database_path) == "0010"
    upgrade_database(database_path)
    assert current_revision(database_path) == LATEST_REVISION


def test_plan_requires_approved_algorithm_and_freezes_with_parent_history(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    create_project(database_path)
    add_algorithm(database_path, status="draft")
    repository = ExperimentRepository(database_path)
    with pytest.raises(ExperimentPlanDecisionConflictError, match="approved algorithm"):
        repository.save_plan(plan())
    engine = create_sqlite_engine(database_path)
    with Session(engine) as session, session.begin():
        session.get(AlgorithmSpecRow, "algo-m7").status = "approved"
    engine.dispose()

    saved = repository.save_plan(plan())
    assert repository.save_plan(plan()) == saved
    assert saved.status == "draft"
    frozen = repository.freeze_plan("lychee-m7", "plan-v1", "researcher-001", "freeze matrix")
    assert frozen.status == "frozen"
    with pytest.raises(ExperimentPlanVersionConflictError, match="frozen parent"):
        repository.save_plan(plan(version=2, objective="Changed mechanism"))
    second = repository.save_plan(plan(version=2, parent="plan-v1", objective="Changed mechanism"))
    assert second.version == 2
    repository.close()


def test_rejected_draft_cannot_be_frozen(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    create_project(database_path)
    add_algorithm(database_path)
    repository = ExperimentRepository(database_path)
    repository.save_plan(plan())
    rejected = repository.reject_plan(
        "lychee-m7", "plan-v1", "researcher-001", "missing data authorization"
    )
    assert rejected.status == "rejected"
    with pytest.raises(ExperimentPlanDecisionConflictError, match="only draft"):
        repository.freeze_plan("lychee-m7", "plan-v1", "researcher-001", "late freeze")
    repository.close()
