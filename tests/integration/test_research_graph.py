from pathlib import Path

import pytest
from pydantic import ValidationError

from scholartrace.graphs.research_project import open_research_project_graph
from scholartrace.persistence.repository import ProjectRepository
from scholartrace.schemas import ResearchQuestion
from scholartrace.states import new_research_project_state


def question() -> ResearchQuestion:
    return ResearchQuestion(
        problem="复杂果园背景中的荔枝病虫害小目标检测",
        target_population_or_domain="华南荔枝果园图像",
        inputs=["RGB 果园图像", "采集条件元数据"],
        expected_outputs=["病虫害类别", "目标边界框"],
        constraints=["类别体系待领域人员确认"],
        success_criteria=["独立测试集指标可复算"],
        assumptions=["正式数据已获得合法授权"],
        unresolved_questions=["小目标尺寸分层阈值如何确定"],
    )


def initial_state(project_id: str, thread_id: str) -> dict[str, object]:
    state = new_research_project_state(
        project_id=project_id,
        thread_id=thread_id,
        current_goal="定义可检验的研究问题",
    )
    state["draft_research_question"] = question()
    return state


def test_graph_has_the_exact_m1_sequence(tmp_path: Path) -> None:
    with open_research_project_graph(
        tmp_path / "domain.db",
        tmp_path / "checkpoints.db",
    ) as workflow:
        edges = {(edge.source, edge.target) for edge in workflow.graph.get_graph().edges}

    assert edges == {
        ("__start__", "intake"),
        ("intake", "build_research_question"),
        ("build_research_question", "save"),
        ("save", "__end__"),
    }


def test_graph_persists_domain_entity_and_checkpoint_across_reopen(tmp_path: Path) -> None:
    domain_path = tmp_path / "domain.db"
    checkpoint_path = tmp_path / "checkpoints.db"
    state = initial_state("lychee-pest-001", "lychee-pest-001")

    with open_research_project_graph(domain_path, checkpoint_path) as workflow:
        result = workflow.invoke(state)

    assert result["active_stage"] == "completed"
    assert result["draft_research_question"] is None
    assert result["research_question_id"].startswith("rq_")

    repository = ProjectRepository(domain_path)
    saved = repository.get_research_question("lychee-pest-001", result["research_question_id"])
    assert saved.question == question()
    assert repository.get_project("lychee-pest-001").active_stage == "completed"
    repository.close()

    with open_research_project_graph(domain_path, checkpoint_path) as reopened:
        snapshot = reopened.get_state("lychee-pest-001")

    assert snapshot["project_id"] == "lychee-pest-001"
    assert snapshot["thread_id"] == "lychee-pest-001"
    assert snapshot["research_question_id"] == result["research_question_id"]
    assert snapshot["active_stage"] == "completed"


def test_replaying_same_input_is_idempotent(tmp_path: Path) -> None:
    domain_path = tmp_path / "domain.db"
    checkpoint_path = tmp_path / "checkpoints.db"
    state = initial_state("lychee-pest-001", "lychee-pest-001")

    with open_research_project_graph(domain_path, checkpoint_path) as workflow:
        first = workflow.invoke(state)
        replay = workflow.invoke(state)

    repository = ProjectRepository(domain_path)
    questions = repository.list_research_questions("lychee-pest-001")
    repository.close()

    assert replay["research_question_id"] == first["research_question_id"]
    assert len(questions) == 1


def test_checkpoint_threads_remain_isolated(tmp_path: Path) -> None:
    domain_path = tmp_path / "domain.db"
    checkpoint_path = tmp_path / "checkpoints.db"

    with open_research_project_graph(domain_path, checkpoint_path) as workflow:
        workflow.invoke(initial_state("project-a", "thread-a"))
        workflow.invoke(initial_state("project-b", "thread-b"))
        project_a = workflow.get_state("thread-a")
        project_b = workflow.get_state("thread-b")

    assert project_a["project_id"] == "project-a"
    assert project_a["thread_id"] == "thread-a"
    assert project_b["project_id"] == "project-b"
    assert project_b["thread_id"] == "thread-b"
    assert project_a["research_question_id"] != project_b["research_question_id"]


def test_invalid_question_does_not_create_domain_question(tmp_path: Path) -> None:
    domain_path = tmp_path / "domain.db"
    checkpoint_path = tmp_path / "checkpoints.db"
    state = initial_state("invalid-question", "invalid-question")
    state["draft_research_question"] = {"problem": "   "}

    with (
        open_research_project_graph(domain_path, checkpoint_path) as workflow,
        pytest.raises(ValidationError),
    ):
        workflow.invoke(state)

    repository = ProjectRepository(domain_path)
    assert repository.list_research_questions("invalid-question") == []
    repository.close()
