import re
from html.parser import HTMLParser
from pathlib import Path

from fastapi.testclient import TestClient

from scholartrace.api import create_app


class _WorkbenchHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.tabs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.add(attributes["id"])
        if attributes.get("data-tab"):
            self.tabs.append(attributes["data-tab"])


def test_workbench_vertical_flow_reaches_paper_draft_and_review_gate(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "domain.db"))
    page = client.get("/")
    assert page.status_code == 200
    assert "研迹 ScholarTrace" in page.text
    assert "论文草稿" in page.text
    assert "/events/stream" in page.text
    assert "提交人工审阅" in page.text
    assert "initialProject" in page.text
    assert "/api/llm/status" in page.text
    assert "/research-question-candidates" in page.text
    assert "candidate 未经验证、不会自动保存" in page.text
    assert "正式保存研究问题" in page.text
    for marker in (
        "/research-questions`",
        "/documents`",
        "/project-documents`",
        "/evidence`",
        "/runs`",
        "/manuscripts`",
        "/figures`",
        "after_sequence=${after}&live=true",
        "['stdout','stderr','system']",
    ):
        assert marker in page.text

    parser = _WorkbenchHTMLParser()
    parser.feed(page.text)
    referenced_ids = set(re.findall(r"\$\('([^']+)'\)", page.text))
    dynamic_ids = set(re.findall(r'id=\\?"([^"\\]+)\\?"', page.text))
    assert referenced_ids <= parser.ids | dynamic_ids
    expected_tabs = {"overview", "question", "literature", "experiments", "manuscript", "figures"}
    assert set(parser.tabs) == expected_tabs
    assert expected_tabs <= parser.ids
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


def test_workbench_navigation_is_usable_before_any_project_exists(tmp_path: Path) -> None:
    """Regression: the sidebar nav must switch visible tabs even with no project.

    Before this fix the whole #workspace section stayed hidden until a project
    was created, so every nav click produced no visible change.
    """

    client = TestClient(create_app(tmp_path / "nav.db"))
    page = client.get("/")
    assert page.status_code == 200

    workspace = '<section id="workspace">'
    assert workspace in page.text  # workspace renders by default (no `hidden`)
    overview_at = page.text.index('id="overview"')
    start_at = page.text.index('id="start"')
    question_at = page.text.index('id="question"')
    assert overview_at < start_at < question_at  # start panel lives inside overview

    # Nav wiring and the no-project guards survive in the shipped script.
    assert "document.querySelectorAll('[data-tab]').forEach" in page.text
    assert "请先在“总览”标签创建或打开项目。" in page.text
    assert "$('start').classList.add('hidden')" in page.text
