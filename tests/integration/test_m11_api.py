from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from scholartrace.api import create_app
from scholartrace.persistence.database import create_sqlite_engine
from scholartrace.persistence.models import AlgorithmSpecRow, ExperimentPlanRow
from scholartrace.persistence.runner_repository import ControlledRunRepository
from scholartrace.schemas import ControlledRunSpec, ResourceLimits


def test_project_api_create_list_get_and_isolate(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "domain.db"))
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    created = client.post(
        "/api/projects",
        json={
            "project_id": "lychee-api",
            "thread_id": "thread-lychee-api",
            "current_goal": "trace the agriculture vision study",
        },
    )
    assert created.status_code == 201
    assert created.json()["active_stage"] == "intake"
    replay = client.post(
        "/api/projects",
        json={
            "project_id": "lychee-api",
            "thread_id": "thread-lychee-api",
            "current_goal": "trace the agriculture vision study",
        },
    )
    assert replay.status_code == 201
    assert len(client.get("/api/projects").json()) == 1
    assert client.get("/api/projects/lychee-api").status_code == 200
    assert client.get("/api/projects/other-api").status_code == 404


def test_run_and_artifact_api_reuse_controlled_repository(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    client = TestClient(create_app(database_path))
    assert (
        client.post(
            "/api/projects",
            json={"project_id": "lychee-api", "thread_id": "thread-lychee-api"},
        ).status_code
        == 201
    )
    engine = create_sqlite_engine(database_path)
    with Session(engine) as session, session.begin():
        session.add(
            AlgorithmSpecRow(
                algorithm_id="algo-api",
                project_id="lychee-api",
                version=1,
                content_sha256="a" * 64,
                payload={},
                status="approved",
                created_by="researcher-001",
                created_at=datetime(2026, 8, 11),
            )
        )
        session.flush()
        session.add(
            ExperimentPlanRow(
                plan_id="plan-api",
                project_id="lychee-api",
                algorithm_id="algo-api",
                version=1,
                content_sha256="b" * 64,
                payload={
                    "matrix": [{"matrix_entry_id": "matrix-api"}],
                    "data_version": "sha256:data-api",
                },
                status="frozen",
                created_by="researcher-001",
                created_at=datetime(2026, 8, 11),
            )
        )
    engine.dispose()
    response = client.post(
        "/api/projects/lychee-api/runs",
        json={
            "execution_id": "execution-api",
            "project_id": "lychee-api",
            "plan_id": "plan-api",
            "matrix_entry_id": "matrix-api",
            "command": ["python", "-m", "pytest"],
            "backend": "local",
            "workspace_relpath": "workspace",
            "input_relpaths": [],
            "output_relpath": "outputs",
            "environment": {},
            "limits": {
                "timeout_seconds": 30,
                "memory_mb": 256,
                "cpu_cores": 1,
            },
            "created_by": "researcher-001",
            "created_at": "2026-08-11T00:00:00Z",
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "queued"
    assert len(client.get("/api/projects/lychee-api/runs").json()) == 1
    assert client.get("/api/projects/lychee-api/artifacts").json() == []


def test_run_events_and_sse_keep_connection_degradable(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    client = TestClient(create_app(database_path))
    client.post(
        "/api/projects",
        json={"project_id": "lychee-api", "thread_id": "thread-lychee-api"},
    )
    engine = create_sqlite_engine(database_path)
    with Session(engine) as session, session.begin():
        session.add(
            AlgorithmSpecRow(
                algorithm_id="algo-api",
                project_id="lychee-api",
                version=1,
                content_sha256="a" * 64,
                payload={},
                status="approved",
                created_by="researcher-001",
                created_at=datetime(2026, 8, 11),
            )
        )
        session.flush()
        session.add(
            ExperimentPlanRow(
                plan_id="plan-api",
                project_id="lychee-api",
                algorithm_id="algo-api",
                version=1,
                content_sha256="b" * 64,
                payload={"matrix": [{"matrix_entry_id": "matrix-api"}]},
                status="frozen",
                created_by="researcher-001",
                created_at=datetime(2026, 8, 11),
            )
        )
    engine.dispose()
    run_repo = ControlledRunRepository(database_path)
    run_repo.create_run(
        ControlledRunSpec(
            execution_id="execution-api",
            project_id="lychee-api",
            plan_id="plan-api",
            matrix_entry_id="matrix-api",
            command=["python", "-m", "pytest"],
            limits=ResourceLimits(
                timeout_seconds=30,
                memory_mb=256,
            ),
            created_by="researcher-001",
            created_at=datetime(2026, 8, 11, tzinfo=UTC),
        )
    )
    run_repo.append_event(
        "lychee-api",
        "execution-api",
        stream="stdout",
        message="run started",
    )
    run_repo.append_event(
        "lychee-api",
        "execution-api",
        stream="system",
        message="run queued",
    )
    run_repo.close()
    events = client.get("/api/projects/lychee-api/runs/execution-api/events")
    assert events.status_code == 200
    assert events.json()[0]["message"] == "run started"
    stream = client.get("/api/projects/lychee-api/runs/execution-api/events/stream")
    assert stream.status_code == 200
    assert "event: stdout" in stream.text
    assert "event: system" in stream.text
    assert "retry: 3000" in stream.text
    assert "keep-alive" in stream.text
    replay = client.get(
        "/api/projects/lychee-api/runs/execution-api/events/stream",
        headers={"Last-Event-ID": "0"},
    )
    assert replay.status_code == 200
    assert "run queued" in replay.text
    assert "run started" not in replay.text
    assert (
        client.get(
            "/api/projects/lychee-api/runs/execution-api/events/stream",
            headers={"Last-Event-ID": "invalid"},
        ).status_code
        == 400
    )


def _research_question(seed: int) -> dict:
    return {
        "problem": f"concurrent research question {seed}",
        "target_population_or_domain": "concurrent test domain",
        "inputs": [f"input-{seed}"],
        "expected_outputs": [f"output-{seed}"],
        "constraints": [f"constraint-{seed}"],
        "success_criteria": [f"criterion-{seed}"],
        "assumptions": [f"assumption-{seed}"],
        "unresolved_questions": [f"question-{seed}"],
    }


def test_api_rejects_invalid_identifiers_with_422(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "domain.db"))
    # Malformed identifiers must be rejected at the API boundary as 422 rather
    # than bubbling out of repository validation as a 500.
    for invalid in ["bad id!", "with/slash", "semi;colon"]:
        response = client.post(
            "/api/projects",
            json={"project_id": invalid, "thread_id": "thread-ok", "current_goal": "g"},
        )
        assert response.status_code == 422, (invalid, response.status_code, response.text)
    # A malformed thread_id is rejected for the same reason.
    response = client.post(
        "/api/projects",
        json={"project_id": "ok-id", "thread_id": "bad thread", "current_goal": "g"},
    )
    assert response.status_code == 422


def test_api_concurrent_question_versions_conflict_cleanly(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "domain.db"))
    project_id = "concurrent-api"
    assert (
        client.post(
            "/api/projects",
            json={"project_id": project_id, "thread_id": f"thread-{project_id}"},
        ).status_code
        == 201
    )

    # Submitting many distinct questions concurrently races the read-then-write
    # version allocation. Losers of the (project_id, version) unique constraint
    # must surface as retriable 409 instead of leaking IntegrityError as 500.
    statuses: list[int] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [
            pool.submit(
                lambda seed: (
                    client.post(
                        f"/api/projects/{project_id}/research-questions",
                        json=_research_question(seed),
                    ).status_code
                ),
                seed,
            )
            for seed in range(24)
        ]
        for future in as_completed(futures):
            statuses.append(future.result())

    assert all(code in {201, 409} for code in statuses), statuses
    assert 500 not in statuses, statuses

    listed = client.get(f"/api/projects/{project_id}/research-questions").json()
    versions = sorted(item["version"] for item in listed)
    assert versions == list(range(1, len(versions) + 1)), versions
    # Persisted versions stay duplicate-free even under contention.
    assert len(versions) == len(set(versions))
