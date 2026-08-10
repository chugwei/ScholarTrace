from datetime import UTC, datetime
from pathlib import Path

import pytest

from scholartrace.persistence.database import create_sqlite_engine
from scholartrace.persistence.experiment_repository import ExperimentRepository
from scholartrace.persistence.migrations import (
    current_revision,
    downgrade_database,
    upgrade_database,
)
from scholartrace.persistence.models import AlgorithmSpecRow
from scholartrace.persistence.repository import ProjectRepository
from scholartrace.persistence.run_repository import (
    RunManifestConflictError,
    RunRepository,
)
from scholartrace.schemas import ExperimentMatrixEntry, ExperimentPlan, RunManifest

CREATED_AT = datetime(2026, 8, 11, tzinfo=UTC)


def create_project(database_path: Path) -> None:
    repository = ProjectRepository(database_path)
    repository.create_project("lychee-m7-run", "lychee-m7-run")
    repository.close()


def add_algorithm(database_path: Path) -> None:
    engine = create_sqlite_engine(database_path)
    from sqlalchemy.orm import Session

    with Session(engine) as session, session.begin():
        session.add(
            AlgorithmSpecRow(
                algorithm_id="algo-m7-run",
                project_id="lychee-m7-run",
                version=1,
                content_sha256="a" * 64,
                payload={},
                status="approved",
                created_by="researcher-001",
                created_at=CREATED_AT.replace(tzinfo=None),
            )
        )
    engine.dispose()


def frozen_plan(database_path: Path) -> None:
    repository = ExperimentRepository(database_path)
    repository.save_plan(
        ExperimentPlan(
            plan_id="plan-run-v1",
            project_id="lychee-m7-run",
            algorithm_id="algo-m7-run",
            version=1,
            objective="Check imported artifact provenance",
            hypotheses=["the imported run keeps its provenance"],
            datasets=["lychee-fixture-v1"],
            baselines=["standard detector"],
            proposed_methods=["proposed detector"],
            independent_variables=["method"],
            controlled_variables=["split"],
            metrics=["recall"],
            seeds=[7],
            repeats=1,
            ablations=["without proposed module"],
            resource_budget={"cpu_hours": 1},
            stopping_criteria=["stop on missing artifact"],
            expected_artifacts=["manifest"],
            failure_and_fallback_plan=["mark incomplete"],
            matrix=[
                ExperimentMatrixEntry(
                    matrix_entry_id="matrix-run",
                    name="proposed",
                    method_kind="proposed",
                    method_ref="proposed detector",
                    dataset_version="lychee-fixture-v1",
                    config_ref="configs/proposed.yaml",
                    seeds=[7],
                    repeats=1,
                    metrics=["recall"],
                )
            ],
            data_version="sha256:fixture-v1",
            code_sha256="b" * 64,
            environment_lock="uv.lock@fixture",
            config_refs=["configs/proposed.yaml"],
            created_by="researcher-001",
            created_at=CREATED_AT,
        )
    )
    repository.freeze_plan("lychee-m7-run", "plan-run-v1", "researcher-001", "freeze")
    repository.close()


def manifest(*, run_id: str = "run-001", complete: bool = True) -> RunManifest:
    return RunManifest(
        run_id=run_id,
        project_id="lychee-m7-run",
        plan_id="plan-run-v1",
        matrix_entry_id="matrix-run",
        code_sha256="c" * 64 if complete else None,
        data_version="sha256:fixture-v1" if complete else None,
        config_ref="configs/proposed.yaml" if complete else None,
        environment_lock="uv.lock@fixture" if complete else None,
        seed=7 if complete else None,
        checkpoint_sha256="d" * 64 if complete else None,
        log_relpath="runs/run-001/train.log" if complete else None,
        config_relpath="runs/run-001/config.yaml" if complete else None,
        weights_relpath="runs/run-001/model.pt" if complete else None,
        metrics_relpath="runs/run-001/metrics.json" if complete else None,
        artifact_relpaths=["runs/run-001/manifest.json"],
        imported_at=CREATED_AT,
    )


def setup(database_path: Path) -> None:
    upgrade_database(database_path)
    create_project(database_path)
    add_algorithm(database_path)
    frozen_plan(database_path)


def test_m7_run_migration_rolls_back(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    assert current_revision(database_path) == "0012"
    downgrade_database(database_path, "0011")
    assert current_revision(database_path) == "0011"
    upgrade_database(database_path)
    assert current_revision(database_path) == "0012"


def test_incomplete_manifest_and_reported_metric_never_become_final(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "domain.db"
    setup(database_path)
    repository = RunRepository(database_path)
    imported = repository.import_manifest(manifest(complete=False))
    assert imported.status == "incomplete"
    assert "code_sha256" in imported.missing_requirements
    metric = repository.import_reported_metric(
        metric_result_id="metric-log-001",
        project_id="lychee-m7-run",
        run_id="run-001",
        name="recall",
        split="validation",
        value=0.91,
        source="training_log",
    )
    assert metric.verification_status == "unverifiable"
    assert metric.is_final is False
    assert repository.list_metrics("lychee-m7-run")[0].is_final is False
    repository.close()


def test_complete_manifest_is_imported_and_paths_are_sandboxed(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    setup(database_path)
    repository = RunRepository(database_path)
    imported = repository.import_manifest(manifest())
    assert imported.status == "imported"
    assert repository.get_manifest("lychee-m7-run", "run-001").status == "imported"
    replay = repository.import_manifest(manifest())
    assert replay.run_id == imported.run_id
    with pytest.raises(ValueError, match="relative"):
        RunManifest.model_validate(
            {**manifest().model_dump(), "log_relpath": "C:/private/train.log"}
        )
    with pytest.raises(RunManifestConflictError):
        repository.import_manifest(manifest().model_copy(update={"run_id": "run-001", "seed": 11}))
    repository.close()
