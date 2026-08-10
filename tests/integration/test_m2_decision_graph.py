from pathlib import Path

import pytest
from langgraph.types import Command

from scholartrace.graphs.research_question_decision import (
    CheckpointNotFoundError,
    open_research_question_decision_graph,
)
from scholartrace.persistence.migrations import upgrade_database
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


def initial_state(project_id: str) -> dict[str, object]:
    state = new_research_project_state(
        project_id=project_id,
        thread_id=project_id,
        current_goal="确认研究问题边界",
    )
    state["research_question_payload"] = complete_payload()
    return state


def start_decision(workflow: object, state: dict[str, object]) -> dict[str, object]:
    return workflow.invoke(state)  # type: ignore[union-attr]


@pytest.mark.parametrize("action", ["rejected", "cancelled", "paused"])
def test_terminal_decisions_are_recorded_without_saving_question(
    tmp_path: Path,
    action: str,
) -> None:
    project_id = f"decision-{action}"
    database_path = tmp_path / f"{action}.domain.db"
    checkpoint_path = tmp_path / f"{action}.checkpoints.db"

    with open_research_question_decision_graph(database_path, checkpoint_path) as workflow:
        paused = start_decision(workflow, initial_state(project_id))
        assert "__interrupt__" in paused
        result = workflow.resume(
            project_id,
            Command(
                resume={
                    "decision_id": f"decision-{action}",
                    "action": action,
                    "actor_id": "researcher-001",
                    "reason": f"人工决定: {action}",
                }
            ),
        )

    assert result["active_stage"] == action
    repository = ProjectRepository(database_path)
    assert repository.list_research_questions(project_id) == []
    decisions = repository.list_decisions(project_id)
    assert len(decisions) == 1
    assert decisions[0].action == action
    repository.close()


def test_approved_decision_saves_question_and_modified_loops_to_review(
    tmp_path: Path,
) -> None:
    project_id = "decision-modified-approved"
    database_path = tmp_path / "domain.db"
    checkpoint_path = tmp_path / "checkpoints.db"

    with open_research_question_decision_graph(database_path, checkpoint_path) as workflow:
        first_pause = start_decision(workflow, initial_state(project_id))
        modified_pause = workflow.resume(
            project_id,
            Command(
                resume={
                    "decision_id": "decision-modified",
                    "action": "modified",
                    "actor_id": "researcher-001",
                    "reason": "补充真实采集条件边界",
                    "fields": {"constraints": ["需覆盖雨季和晴天"]},
                }
            ),
        )
        approved = workflow.resume(
            project_id,
            Command(
                resume={
                    "decision_id": "decision-approved",
                    "action": "approved",
                    "actor_id": "researcher-001",
                    "reason": "人工确认修改后的研究问题",
                }
            ),
        )

    assert "__interrupt__" in first_pause
    assert "__interrupt__" in modified_pause
    assert approved["active_stage"] == "completed"
    repository = ProjectRepository(database_path)
    assert len(repository.list_research_questions(project_id)) == 1
    assert [item.action for item in repository.list_decisions(project_id)] == [
        "modified",
        "approved",
    ]
    repository.close()


def test_approved_revision_descends_from_frozen_question(tmp_path: Path) -> None:
    project_id = "decision-revision"
    database_path = tmp_path / "domain.db"
    checkpoint_path = tmp_path / "checkpoints.db"
    upgrade_database(database_path)

    repository = ProjectRepository(database_path)
    repository.create_project(
        project_id,
        project_id,
        current_goal="确认研究问题边界",
    )
    base = repository.save_research_question(
        project_id,
        ResearchQuestion.model_validate(complete_payload()),
    )
    repository.freeze_research_question(project_id, base.research_question_id, "researcher-001")
    repository.close()

    state = initial_state(project_id)
    state["research_question_id"] = base.research_question_id
    revised_payload = complete_payload()
    revised_payload["constraints"] = ["需覆盖雨季和晴天"]
    state["research_question_payload"] = revised_payload

    with open_research_question_decision_graph(database_path, checkpoint_path) as workflow:
        start_decision(workflow, state)
        result = workflow.resume(
            project_id,
            Command(
                resume={
                    "decision_id": "decision-revision-approved",
                    "action": "approved",
                    "actor_id": "researcher-001",
                    "reason": "批准新的采集条件边界",
                }
            ),
        )

    assert result["active_stage"] == "completed"
    assert result["research_question_id"] != base.research_question_id
    repository = ProjectRepository(database_path)
    versions = repository.list_research_questions(project_id)
    assert [(item.version, item.status) for item in versions] == [(1, "frozen"), (2, "frozen")]
    assert versions[1].parent_research_question_id == base.research_question_id
    repository.close()


def test_decision_request_requires_human_actor_and_reason(tmp_path: Path) -> None:
    project_id = "decision-invalid"
    database_path = tmp_path / "domain.db"
    checkpoint_path = tmp_path / "checkpoints.db"

    with open_research_question_decision_graph(database_path, checkpoint_path) as workflow:
        start_decision(workflow, initial_state(project_id))
        with pytest.raises(Exception, match=r"actor_id|reason"):
            workflow.resume(
                project_id,
                Command(
                    resume={
                        "decision_id": "decision-invalid",
                        "action": "rejected",
                        "actor_id": "   ",
                        "reason": "需要重新确认",
                    }
                ),
            )


def test_modified_decision_rejects_unknown_fields_before_recording(tmp_path: Path) -> None:
    project_id = "decision-invalid-modification"
    database_path = tmp_path / "domain.db"
    checkpoint_path = tmp_path / "checkpoints.db"

    with open_research_question_decision_graph(database_path, checkpoint_path) as workflow:
        start_decision(workflow, initial_state(project_id))
        with pytest.raises(ValueError, match="unknown names"):
            workflow.resume(
                project_id,
                Command(
                    resume={
                        "decision_id": "decision-invalid-modification",
                        "action": "modified",
                        "actor_id": "researcher-001",
                        "reason": "需要重新确认",
                        "fields": {"invented_field": ["不可作为研究问题字段"]},
                    }
                ),
            )

    repository = ProjectRepository(database_path)
    assert repository.list_decisions(project_id) == []
    repository.close()


def test_checkpoint_history_rollback_creates_new_checkpoint_and_audit_record(
    tmp_path: Path,
) -> None:
    project_id = "decision-history"
    database_path = tmp_path / "domain.db"
    checkpoint_path = tmp_path / "checkpoints.db"

    with open_research_question_decision_graph(database_path, checkpoint_path) as workflow:
        start_decision(workflow, initial_state(project_id))
        before_approval = next(
            snapshot
            for snapshot in workflow.history(project_id)
            if snapshot.values.get("active_stage") == "awaiting_approval"
        )
        before_id = before_approval.config["configurable"]["checkpoint_id"]
        initial_history_length = len(workflow.history(project_id))

        workflow.resume(
            project_id,
            Command(
                resume={
                    "decision_id": "decision-history-approved",
                    "action": "approved",
                    "actor_id": "researcher-001",
                    "reason": "先批准以验证回滚",
                }
            ),
        )
        completed = workflow.get_state(project_id)
        assert completed.values["active_stage"] == "completed"

        restored = workflow.rollback(
            project_id,
            before_id,
            actor_id="researcher-001",
            reason="重新检查批准前的研究问题边界",
        )
        assert restored["active_stage"] == "awaiting_approval"
        assert restored["research_question_id"] is None
        assert len(workflow.history(project_id)) > initial_history_length

        with pytest.raises(CheckpointNotFoundError, match="was not found"):
            workflow.rollback(
                project_id,
                "missing-checkpoint",
                actor_id="researcher-001",
                reason="不存在的 checkpoint",
            )

    repository = ProjectRepository(database_path)
    audits = repository.list_audit_records(project_id)
    assert [item.action for item in audits] == ["approved", "rolled_back"]
    assert audits[-1].target_type == "checkpoint"
    assert audits[-1].target_id == before_id
    assert repository.list_decisions(project_id, action="rolled_back") == [audits[-1]]
    repository.close()

    with open_research_question_decision_graph(database_path, checkpoint_path) as reopened:
        assert reopened.get_state(project_id).values["active_stage"] == "awaiting_approval"
        assert len(reopened.get_state_history(project_id, limit=2)) == 2
