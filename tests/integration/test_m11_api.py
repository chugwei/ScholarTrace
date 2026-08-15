from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from scholartrace.api import create_app
from scholartrace.persistence.database import create_sqlite_engine
from scholartrace.persistence.literature_repository import (
    LiteratureRepository,
    document_id_for_content,
)
from scholartrace.persistence.models import AlgorithmSpecRow, ExperimentPlanRow
from scholartrace.persistence.runner_repository import ControlledRunRepository
from scholartrace.schemas import ControlledRunSpec, Document, DocumentMetadata, ResourceLimits


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


def test_research_question_candidate_api_returns_503_without_provider(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.delenv("SCHOLARTRACE_LLM_API_KEY", raising=False)
    client = TestClient(create_app(tmp_path / "domain.db"))
    client.post(
        "/api/projects",
        json={"project_id": "llm-api", "thread_id": "thread-llm-api"},
    )

    response = client.post(
        "/api/projects/llm-api/research-question-candidates",
        json={"problem": "荔枝病虫害检测"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "LLM provider is not configured"
    assert client.get("/api/llm/status").json() == {
        "enabled": False,
        "provider": None,
        "model": None,
    }


class _FakeLLMProvider:
    name = "fake-provider"
    model = "fake-model"

    def __init__(self) -> None:
        self.input_payload: object = None

    def generate_json(
        self,
        *,
        system_prompt: str,
        input_payload,
    ) -> dict[str, object]:
        assert "unverified" not in system_prompt
        self.input_payload = input_payload
        return {
            "problem": "复杂果园背景中的荔枝病虫害小目标检测",
            "target_population_or_domain": "华南荔枝果园图像",
            "inputs": ["RGB 果园图像"],
            "expected_outputs": ["病虫害类别", "目标边界框"],
            "constraints": ["类别体系尚待确认"],
            "success_criteria": ["独立测试集指标可复算"],
            "assumptions": ["正式数据已获合法授权"],
            "unresolved_questions": ["小目标分层阈值如何确定"],
        }


def test_research_question_candidate_api_does_not_persist_fake_llm_output(
    tmp_path: Path,
) -> None:
    provider = _FakeLLMProvider()
    client = TestClient(create_app(tmp_path / "domain.db", llm_provider=provider))
    assert client.get("/api/llm/status").json() == {
        "enabled": True,
        "provider": "fake-provider",
        "model": "fake-model",
    }
    assert (
        client.post(
            "/api/projects",
            json={"project_id": "llm-api", "thread_id": "thread-llm-api"},
        ).status_code
        == 201
    )

    response = client.post(
        "/api/projects/llm-api/research-question-candidates",
        json={
            "problem": "荔枝病虫害检测",
            "context": "仅使用已审阅项目上下文",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "candidate"
    assert payload["provider"] == "fake-provider"
    assert payload["model"] == "fake-model"
    assert payload["candidate"]["problem"] == "复杂果园背景中的荔枝病虫害小目标检测"
    assert payload["warnings"]
    assert provider.input_payload == {
        "problem": "荔枝病虫害检测",
        "context": "仅使用已审阅项目上下文",
    }
    assert client.get("/api/projects/llm-api/research-questions").json() == []


def _catalog_document(
    content_sha256: str,
    title: str,
    *,
    searchable: bool = True,
) -> Document:
    return Document(
        document_id=document_id_for_content(content_sha256),
        content_sha256=content_sha256,
        mime_type="application/pdf",
        byte_size=128,
        source_type="uploaded_pdf",
        ingest_status="indexed" if searchable else "failed",
        quality_status="ok" if searchable else "parse_failed",
        searchable=searchable,
        metadata=DocumentMetadata(
            title=title,
            authors=["Researcher One"],
            year=2024,
            doi="10.1234/scholartrace.test" if searchable else None,
        ),
        created_at=datetime(2026, 8, 13, tzinfo=UTC),
    )


def test_project_document_api_lists_metadata_and_records_human_reviews(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    client = TestClient(create_app(database_path))
    project_id = "literature-api"
    assert (
        client.post(
            "/api/projects",
            json={"project_id": project_id, "thread_id": f"thread-{project_id}"},
        ).status_code
        == 201
    )
    repository = LiteratureRepository(database_path)
    documents = [
        repository.save_document(_catalog_document("a" * 64, "Approved orchard study")),
        repository.save_document(_catalog_document("b" * 64, "Rejected wheat study")),
        repository.save_document(_catalog_document("c" * 64, "Candidate review queue")),
    ]
    for document in documents:
        repository.attach_document(project_id, document.document_id)
    repository.close()

    approved = client.post(
        f"/api/projects/{project_id}/project-documents/{documents[0].document_id}/review",
        json={
            "status": "approved",
            "actor_id": "researcher-001",
            "reason": "来源和研究域经人工核验",
            "relevance_score": 0.91,
        },
    )
    rejected = client.post(
        f"/api/projects/{project_id}/project-documents/{documents[1].document_id}/review",
        json={
            "status": "rejected",
            "actor_id": "researcher-001",
            "reason": "研究对象不匹配",
            "relevance_score": 0.08,
        },
    )

    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["decided_by"] == "researcher-001"
    assert approved.json()["relevance_score"] == 0.91
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    response = client.get(f"/api/projects/{project_id}/project-documents")
    assert response.status_code == 200
    listed = {item["document"]["document_id"]: item for item in response.json()}
    assert {item["link"]["status"] for item in listed.values()} == {
        "candidate",
        "approved",
        "rejected",
    }
    assert listed[documents[0].document_id]["document"]["metadata"] == {
        "title": "Approved orchard study",
        "authors": ["Researcher One"],
        "abstract": None,
        "year": 2024,
        "doi": "10.1234/scholartrace.test",
        "url": None,
    }
    approved_documents = client.get(f"/api/projects/{project_id}/documents").json()
    assert [item["document_id"] for item in approved_documents] == [documents[0].document_id]


def test_project_document_api_rejects_missing_candidate_and_unsafe_approval(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "domain.db"
    client = TestClient(create_app(database_path))
    project_id = "literature-review-errors"
    client.post(
        "/api/projects",
        json={"project_id": project_id, "thread_id": f"thread-{project_id}"},
    )
    repository = LiteratureRepository(database_path)
    unattached = repository.save_document(_catalog_document("d" * 64, "Unattached source"))
    unsafe = repository.save_document(_catalog_document("e" * 64, "Failed parse", searchable=False))
    repository.attach_document(project_id, unsafe.document_id)
    repository.close()
    review = {
        "status": "approved",
        "actor_id": "researcher-001",
        "reason": "manual review",
    }

    missing_candidate = client.post(
        f"/api/projects/{project_id}/project-documents/{unattached.document_id}/review",
        json=review,
    )
    unsafe_approval = client.post(
        f"/api/projects/{project_id}/project-documents/{unsafe.document_id}/review",
        json=review,
    )

    assert missing_candidate.status_code == 409
    assert "attached as candidate" in missing_candidate.json()["detail"]
    assert unsafe_approval.status_code == 422
    assert "cannot be approved" in unsafe_approval.json()["detail"]
