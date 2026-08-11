from pathlib import Path

from fastapi.testclient import TestClient

from scholartrace.api import create_app


def test_workbench_vertical_flow_reaches_paper_draft_and_review_gate(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "domain.db"))
    page = client.get("/")
    assert page.status_code == 200
    assert "研迹 ScholarTrace" in page.text
    assert "论文草稿" in page.text
    assert "/events/stream" in page.text
    assert "提交人工审阅" in page.text
    assert "initialProject" in page.text
    project_id = "lychee-workbench"
    assert (
        client.post(
            "/api/projects",
            json={
                "project_id": project_id,
                "thread_id": "thread-lychee-workbench",
                "current_goal": "trace an agriculture vision study",
            },
        ).status_code
        == 201
    )
    question = {
        "problem": "How can orchard images support traceable pest detection?",
        "target_population_or_domain": "lychee orchard images",
        "inputs": ["field images"],
        "expected_outputs": ["pest categories"],
        "constraints": ["preserve data version"],
        "success_criteria": ["independent validation"],
        "assumptions": ["fixture images are synthetic"],
        "unresolved_questions": ["field ethics review"],
    }
    assert (
        client.post(f"/api/projects/{project_id}/research-questions", json=question).status_code
        == 201
    )
    assert len(client.get(f"/api/projects/{project_id}/research-questions").json()) == 1
    manuscript = client.post(
        f"/api/projects/{project_id}/manuscripts",
        json={"title": "Traceable orchard vision draft", "target_template": "journal_article"},
    )
    assert manuscript.status_code == 201
    manuscript_id = manuscript.json()["manuscript_id"]
    draft = client.get(f"/api/projects/{project_id}/manuscripts/{manuscript_id}/draft")
    assert draft.status_code == 200
    assert len(draft.json()["sections"]) == 4
    assert draft.json()["errors"] == []
    review = client.post(
        f"/api/projects/{project_id}/manuscripts/{manuscript_id}/review",
        json={"actor_id": "researcher-001", "reason": "human review of the generated structure"},
    )
    assert review.status_code == 200
    assert review.json()["status"] == "in_review"
    assert client.get(f"/api/projects/{project_id}/documents").json() == []
    assert client.get(f"/api/projects/{project_id}/evidence").json() == []
    assert client.get(f"/api/projects/{project_id}/figures").json() == []
