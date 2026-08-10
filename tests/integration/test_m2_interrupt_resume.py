from pathlib import Path

from langgraph.types import Command

from scholartrace.graphs.research_question_approval import (
    open_research_question_approval_graph,
)
from scholartrace.persistence.repository import ProjectRepository
from scholartrace.schemas import ResearchQuestion
from scholartrace.states import new_research_project_state, replace_strings


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


def incomplete_state(project_id: str = "lychee-m2-interrupt") -> dict[str, object]:
    state = new_research_project_state(
        project_id=project_id,
        thread_id=project_id,
        current_goal="确认研究问题边界",
    )
    state["research_question_payload"] = {"problem": complete_payload()["problem"]}
    return state


def test_pending_question_reducer_replaces_current_gap_without_duplicates() -> None:
    assert replace_strings(["problem", "inputs"], ["target_population_or_domain"]) == [
        "target_population_or_domain"
    ]
    assert replace_strings(["problem"], ["problem", "problem"]) == ["problem"]


def test_interrupt_persists_and_command_resume_completes_after_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    checkpoint_path = tmp_path / "checkpoints.db"
    state = incomplete_state()

    with open_research_question_approval_graph(database_path, checkpoint_path) as workflow:
        paused = workflow.invoke(state)

    assert "__interrupt__" in paused
    interrupt_payload = paused["__interrupt__"][0].value
    assert interrupt_payload["kind"] == "research_question_clarification"
    assert paused["active_stage"] == "awaiting_clarification"
    assert "target_population_or_domain" in interrupt_payload["missing_fields"]

    answer = complete_payload()
    answer.pop("problem")
    with open_research_question_approval_graph(database_path, checkpoint_path) as reopened:
        resumed = reopened.resume(
            "lychee-m2-interrupt",
            Command(resume=answer),
        )

    assert resumed["active_stage"] == "completed"
    assert resumed["pending_questions"] == []
    assert resumed["research_question_id"].startswith("rq_")
    repository = ProjectRepository(database_path)
    assert len(repository.list_research_questions("lychee-m2-interrupt")) == 1
    repository.close()


def test_invalid_resume_answer_interrupts_again_without_saving(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    checkpoint_path = tmp_path / "checkpoints.db"
    state = incomplete_state("lychee-m2-invalid-resume")

    with open_research_question_approval_graph(database_path, checkpoint_path) as workflow:
        workflow.invoke(state)
        paused_again = workflow.resume(
            "lychee-m2-invalid-resume",
            Command(resume={"target_population_or_domain": "果园图像"}),
        )

    assert "__interrupt__" in paused_again
    assert paused_again["active_stage"] == "awaiting_clarification"
    repository = ProjectRepository(database_path)
    assert repository.list_research_questions("lychee-m2-invalid-resume") == []
    repository.close()


def test_approval_checkpoint_reports_waiting_task_after_process_boundary(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    checkpoint_path = tmp_path / "checkpoints.db"

    with open_research_question_approval_graph(database_path, checkpoint_path) as workflow:
        workflow.invoke(incomplete_state("lychee-m2-history"))

    with open_research_question_approval_graph(database_path, checkpoint_path) as reopened:
        snapshot = reopened.get_state("lychee-m2-history")

    assert snapshot.values["active_stage"] == "awaiting_clarification"
    assert snapshot.tasks
    assert snapshot.tasks[0].interrupts
