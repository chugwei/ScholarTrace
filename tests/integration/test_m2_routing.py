from pathlib import Path

import pytest

from scholartrace.graphs.research_question_review import open_research_question_review_graph
from scholartrace.persistence.repository import ProjectRepository
from scholartrace.schemas import ResearchQuestion
from scholartrace.states import new_research_project_state


def complete_payload() -> dict[str, object]:
    return ResearchQuestion(
        problem="复杂果园背景、遮挡和小目标条件下的荔枝病虫害目标检测",
        target_population_or_domain="合成、脱敏的华南荔枝果园视觉场景描述",
        inputs=["脱敏的场景类别描述", "标注 Schema 示例"],
        expected_outputs=["病虫害检测候选", "按场景条件分组的错误分析计划"],
        constraints=["不得将 Fixture 结果描述为真实果园指标"],
        success_criteria=["研究问题包含目标、输入、输出、限制和待确认项"],
        assumptions=["正式类别体系和采集授权尚未确定"],
        unresolved_questions=["小目标尺寸分层的验收阈值如何确定"],
    ).model_dump(mode="json")


def new_state(project_id: str = "lychee-m2-001") -> dict[str, object]:
    return new_research_project_state(
        project_id=project_id,
        thread_id=project_id,
        current_goal="确认研究问题边界",
    )


def test_conditional_route_has_clarification_and_continue_edges(tmp_path: Path) -> None:
    with open_research_question_review_graph(
        tmp_path / "domain.db",
        tmp_path / "checkpoints.db",
    ) as workflow:
        edges = {(edge.source, edge.target) for edge in workflow.graph.get_graph().edges}

    assert ("__start__", "intake") in edges
    assert ("intake", "clarify") in edges
    assert ("intake", "build_research_question") in edges
    assert ("build_research_question", "save") in edges
    assert ("save", "__end__") in edges
    assert ("clarify", "__end__") in edges


def test_missing_fields_take_clarification_route_without_persisting_question(
    tmp_path: Path,
) -> None:
    state = new_state()
    state["research_question_payload"] = {
        "problem": "   ",
        "target_population_or_domain": "果园图像",
        "inputs": [],
    }

    with open_research_question_review_graph(
        tmp_path / "domain.db",
        tmp_path / "checkpoints.db",
    ) as workflow:
        result = workflow.invoke(state)

    assert result["active_stage"] == "awaiting_clarification"
    assert result["pending_questions"] == [
        "problem",
        "inputs",
        "expected_outputs",
        "constraints",
        "success_criteria",
        "assumptions",
        "unresolved_questions",
    ]
    repository = ProjectRepository(tmp_path / "domain.db")
    assert repository.list_research_questions("lychee-m2-001") == []
    repository.close()


def test_complete_payload_continues_and_saves(tmp_path: Path) -> None:
    state = new_state()
    state["research_question_payload"] = complete_payload()

    with open_research_question_review_graph(
        tmp_path / "domain.db",
        tmp_path / "checkpoints.db",
    ) as workflow:
        result = workflow.invoke(state)

    assert result["active_stage"] == "completed"
    assert result["pending_questions"] == []
    assert result["research_question_id"].startswith("rq_")


@pytest.mark.parametrize(
    "field",
    ["problem", "target_population_or_domain", "inputs", "expected_outputs", "success_criteria"],
)
def test_each_core_missing_field_is_reported_deterministically(
    tmp_path: Path,
    field: str,
) -> None:
    payload = complete_payload()
    payload[field] = "   " if field in {"problem", "target_population_or_domain"} else []
    state = new_state(f"missing-{field}")
    state["research_question_payload"] = payload

    with open_research_question_review_graph(
        tmp_path / f"{field}.domain.db",
        tmp_path / f"{field}.checkpoints.db",
    ) as workflow:
        result = workflow.invoke(state)

    assert result["active_stage"] == "awaiting_clarification"
    assert field in result["pending_questions"]
