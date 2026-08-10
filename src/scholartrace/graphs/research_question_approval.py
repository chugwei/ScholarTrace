"""M2.2 human clarification with a real interrupt/resume boundary."""

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from scholartrace.graphs.research_question_review import (
    _payload_from_state,
    find_missing_question_fields,
)
from scholartrace.persistence.migrations import upgrade_database
from scholartrace.persistence.repository import ProjectRepository
from scholartrace.schemas import ResearchQuestion
from scholartrace.states import ResearchProjectState


class ResearchQuestionApprovalGraph:
    """Compiled M2.2 graph with explicit invoke, resume, and snapshot methods."""

    def __init__(self, graph: Any) -> None:
        self.graph = graph

    def invoke(self, state: ResearchProjectState) -> dict[str, Any]:
        return cast(dict[str, Any], self.graph.invoke(state, _config(state["thread_id"])))

    def resume(self, thread_id: str, command: Command) -> dict[str, Any]:
        return cast(dict[str, Any], self.graph.invoke(command, _config(thread_id)))

    def get_state(self, thread_id: str) -> Any:
        return self.graph.get_state(_config(thread_id))


def build_research_question_approval_graph(
    repository: ProjectRepository,
    checkpointer: BaseCheckpointSaver[Any],
) -> ResearchQuestionApprovalGraph:
    """Build intake → conditional route → interrupt/resume → save."""

    def intake(state: ResearchProjectState) -> dict[str, Any]:
        repository.create_project(
            project_id=state["project_id"],
            thread_id=state["thread_id"],
            current_goal=state["current_goal"],
        )
        payload = _payload_from_state(state)
        missing = find_missing_question_fields(payload)
        return {
            "active_stage": "awaiting_clarification" if missing else "intake",
            "pending_questions": missing,
            "research_question_payload": payload,
        }

    def route_after_intake(state: ResearchProjectState) -> str:
        return "clarify" if state["pending_questions"] else "build_research_question"

    def clarify(state: ResearchProjectState) -> dict[str, Any]:
        answer = interrupt(
            {
                "kind": "research_question_clarification",
                "missing_fields": state["pending_questions"],
                "payload": state["research_question_payload"],
            }
        )
        if not isinstance(answer, Mapping):
            raise ValueError("clarification resume value must be a mapping")
        payload = dict(state["research_question_payload"] or {})
        payload.update(answer)
        return {
            "active_stage": "intake",
            "pending_questions": [],
            "research_question_payload": payload,
        }

    def build_research_question(state: ResearchProjectState) -> dict[str, Any]:
        question = ResearchQuestion.model_validate(state["research_question_payload"])
        return {
            "active_stage": "save",
            "draft_research_question": question,
        }

    def save(state: ResearchProjectState) -> dict[str, Any]:
        question = ResearchQuestion.model_validate(state["draft_research_question"])
        record = repository.save_research_question(
            state["project_id"],
            question,
            active_stage="completed",
        )
        return {
            "active_stage": "completed",
            "draft_research_question": None,
            "research_question_id": record.research_question_id,
        }

    builder = StateGraph(ResearchProjectState)
    builder.add_node("intake", intake)
    builder.add_node("clarify", clarify)
    builder.add_node("build_research_question", build_research_question)
    builder.add_node("save", save)
    builder.add_edge(START, "intake")
    builder.add_conditional_edges(
        "intake",
        route_after_intake,
        {
            "clarify": "clarify",
            "build_research_question": "build_research_question",
        },
    )
    builder.add_edge("clarify", "intake")
    builder.add_edge("build_research_question", "save")
    builder.add_edge("save", END)
    return ResearchQuestionApprovalGraph(builder.compile(checkpointer=checkpointer))


@contextmanager
def open_research_question_approval_graph(
    database_path: Path,
    checkpoint_path: Path,
) -> Iterator[ResearchQuestionApprovalGraph]:
    """Open the M2.2 graph with a disk-backed checkpointer."""

    resolved_checkpoint_path = checkpoint_path.expanduser().resolve()
    resolved_checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    upgrade_database(database_path)
    repository = ProjectRepository(database_path)
    try:
        with SqliteSaver.from_conn_string(str(resolved_checkpoint_path)) as checkpointer:
            yield build_research_question_approval_graph(repository, checkpointer)
    finally:
        repository.close()


def _config(thread_id: str) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": thread_id}}
