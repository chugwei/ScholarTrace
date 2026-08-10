from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from scholartrace.persistence.database import create_sqlite_engine
from scholartrace.persistence.experiment_repository import ExperimentRepository
from scholartrace.persistence.migrations import (
    current_revision,
    downgrade_database,
    upgrade_database,
)
from scholartrace.persistence.models import AlgorithmSpecRow
from scholartrace.persistence.repository import ProjectRepository
from scholartrace.persistence.runner_repository import (
    ControlledRunConflictError,
    ControlledRunRepository,
    ControlledRunRepositoryError,
)
from scholartrace.runner import CommandPolicy, DockerCommandBuilder, UnsafeCommandError
from scholartrace.schemas import (
    ControlledRunSpec,
    ExperimentMatrixEntry,
    ExperimentPlan,
    ResourceLimits,
)

CREATED_AT = datetime(2026, 8, 11, tzinfo=UTC)


def _plan(database_path: Path, *, status: str = "frozen") -> None:
    project = ProjectRepository(database_path)
    project.create_project("lychee-m8", "lychee-m8")
    project.close()
    engine = create_sqlite_engine(database_path)
    with Session(engine) as session, session.begin():
        session.add(
            AlgorithmSpecRow(
                algorithm_id="algo-m8",
                project_id="lychee-m8",
                version=1,
                content_sha256="a" * 64,
                payload={},
                status="approved",
                created_by="researcher-001",
                created_at=CREATED_AT.replace(tzinfo=None),
            )
        )
    engine.dispose()
    repository = ExperimentRepository(database_path)
    repository.save_plan(
        ExperimentPlan(
            plan_id="plan-m8-v1",
            project_id="lychee-m8",
            algorithm_id="algo-m8",
            version=1,
            objective="verify controlled execution boundaries",
            hypotheses=["isolated output survives a failed run"],
            datasets=["lychee-fixture-v1"],
            baselines=["standard detector"],
            proposed_methods=["safe runner"],
            independent_variables=["runner backend"],
            controlled_variables=["seed"],
            metrics=["accuracy"],
            seeds=[7],
            repeats=1,
            ablations=["without runner"],
            resource_budget={"cpu_hours": 1},
            stopping_criteria=["stop on unsafe command"],
            expected_artifacts=["run manifest"],
            failure_and_fallback_plan=["preserve staging artifacts"],
            matrix=[
                ExperimentMatrixEntry(
                    matrix_entry_id="matrix-m8",
                    name="proposed",
                    method_kind="proposed",
                    method_ref="safe runner",
                    dataset_version="lychee-fixture-v1",
                    config_ref="configs/proposed.yaml",
                    seeds=[7],
                    repeats=1,
                    metrics=["accuracy"],
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
    if status == "frozen":
        repository.freeze_plan("lychee-m8", "plan-m8-v1", "researcher-001", "freeze")
    repository.close()


def _spec(*, execution_id: str = "exec-001", command: list[str] | None = None) -> ControlledRunSpec:
    return ControlledRunSpec(
        execution_id=execution_id,
        project_id="lychee-m8",
        plan_id="plan-m8-v1",
        matrix_entry_id="matrix-m8",
        command=command or ["python", "-m", "pytest", "-q"],
        limits=ResourceLimits(timeout_seconds=30, memory_mb=256, cpu_seconds=20),
        created_by="researcher-001",
        created_at=CREATED_AT,
    )


def test_runner_migration_rolls_back(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    assert current_revision(database_path) == "0014"
    downgrade_database(database_path, "0013")
    assert current_revision(database_path) == "0013"
    upgrade_database(database_path)
    assert current_revision(database_path) == "0014"


def test_policy_rejects_shell_and_inline_code() -> None:
    policy = CommandPolicy()
    with pytest.raises(UnsafeCommandError, match="metacharacters"):
        policy.validate(["python", "script.py; rm -rf outputs"])
    with pytest.raises(UnsafeCommandError, match="inline"):
        policy.validate(["python", "-c", "print('unsafe')"])
    with pytest.raises(UnsafeCommandError, match="allowlisted"):
        policy.validate(["python", "-m", "pip"])


def test_spec_rejects_path_escape_and_invalid_backend() -> None:
    with pytest.raises(ValueError, match="must not escape"):
        ControlledRunSpec.model_validate(
            _spec().model_dump(mode="json") | {"output_relpath": "../formal"}
        )
    with pytest.raises(ValueError, match="docker runs require an image"):
        ControlledRunSpec.model_validate(_spec().model_dump(mode="json") | {"backend": "docker"})


def test_docker_command_is_argv_only_and_inputs_are_read_only(tmp_path: Path) -> None:
    spec = _spec().model_copy(update={"backend": "docker", "image": "python:3.12-slim"})
    command = DockerCommandBuilder().build(
        spec,
        workspace=tmp_path / "workspace",
        outputs=tmp_path / "outputs",
    )
    assert command[:5] == ["docker", "run", "--rm", "--network", "none"]
    assert "--read-only" in command
    assert ":ro" in next(value for value in command if str(value).endswith(":ro"))
    assert "shell=True" not in command


def test_controlled_run_requires_frozen_plan_and_is_idempotent(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    _plan(database_path)
    repository = ControlledRunRepository(database_path)
    created = repository.create_run(_spec())
    assert created.status == "queued"
    assert len(created.command_sha256) == 64
    assert repository.create_run(_spec()) == created
    with pytest.raises(ControlledRunConflictError):
        repository.create_run(_spec(command=["python", "-m", "pytest", "tests"]))
    assert repository.list_runs("lychee-m8")[0].execution_id == "exec-001"
    repository.close()


def test_controlled_run_rejects_draft_plan(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    _plan(database_path, status="draft")
    repository = ControlledRunRepository(database_path)
    with pytest.raises(ControlledRunRepositoryError, match="frozen"):
        repository.create_run(_spec())
    repository.close()
