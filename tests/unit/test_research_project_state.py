import pytest
from langchain_core.messages import HumanMessage
from langgraph.graph.message import add_messages

from scholartrace.states.research_project import (
    merge_unique_strings,
    new_research_project_state,
)


def test_new_state_has_explicit_m1_defaults() -> None:
    state = new_research_project_state(
        project_id="agri-vision-001",
        thread_id="agri-vision-001",
        current_goal="定义可检验的研究问题",
    )

    assert state["project_id"] == "agri-vision-001"
    assert state["thread_id"] == "agri-vision-001"
    assert state["active_stage"] == "intake"
    assert state["current_goal"] == "定义可检验的研究问题"
    assert state["research_question_id"] is None
    assert state["draft_research_question"] is None
    assert state["messages"] == []
    assert state["warnings"] == []
    assert state["artifact_ids"] == []


def test_new_state_does_not_share_mutable_lists_between_projects() -> None:
    first = new_research_project_state("project-a", "project-a")
    second = new_research_project_state("project-b", "project-b")

    first["warnings"].append("only project-a")
    first["messages"].append(HumanMessage(content="isolated"))

    assert second["warnings"] == []
    assert second["messages"] == []


def test_unique_string_reducer_is_ordered_idempotent_and_non_mutating() -> None:
    left = ["clarify-metric", "confirm-domain"]
    right = ["confirm-domain", "freeze-question"]

    merged = merge_unique_strings(left, right)

    assert merged == ["clarify-metric", "confirm-domain", "freeze-question"]
    assert merge_unique_strings(merged, right) == merged
    assert left == ["clarify-metric", "confirm-domain"]
    assert right == ["confirm-domain", "freeze-question"]


def test_langgraph_message_reducer_replaces_matching_message_id() -> None:
    original = HumanMessage(content="old", id="message-1")
    replacement = HumanMessage(content="corrected", id="message-1")

    merged = add_messages([original], [replacement])

    assert len(merged) == 1
    assert merged[0].content == "corrected"


@pytest.mark.parametrize(
    ("project_id", "thread_id"),
    [
        ("", "thread-1"),
        ("project/escape", "thread-1"),
        ("project-1", "thread\\escape"),
        (" project-1", "thread-1"),
    ],
)
def test_new_state_rejects_unsafe_identifiers(project_id: str, thread_id: str) -> None:
    with pytest.raises(ValueError, match="identifier"):
        new_research_project_state(project_id, thread_id)
