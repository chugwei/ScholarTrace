"""M1 persistent research-question workflow."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from scholartrace.identifiers import validate_identifier
from scholartrace.persistence.migrations import upgrade_database
from scholartrace.persistence.repository import ProjectRepository
from scholartrace.schemas import ResearchQuestion
from scholartrace.states import ResearchProjectState


class PersistentResearchProjectGraph:
    """Small facade that binds invocations to their validated thread IDs."""

    def __init__(self, graph: Any) -> None:
        self.graph = graph

    def invoke(self, state: ResearchProjectState) -> ResearchProjectState:
        thread_id = validate_identifier(state["thread_id"])
        result = self.graph.invoke(state, config=_thread_config(thread_id))
        return cast(ResearchProjectState, result)

    def get_state(self, thread_id: str) -> ResearchProjectState:
        snapshot = self.graph.get_state(_thread_config(validate_identifier(thread_id)))
        return cast(ResearchProjectState, snapshot.values)


def build_research_project_graph(
    repository: ProjectRepository,
    checkpointer: BaseCheckpointSaver[Any],
) -> PersistentResearchProjectGraph:
    """Build the exact START → intake → build → save → END M1 graph."""

    def intake(state: ResearchProjectState) -> dict[str, Any]:
        repository.create_project(
            project_id=state["project_id"],
            thread_id=state["thread_id"],
            current_goal=state["current_goal"],
        )
        return {"active_stage": "build_research_question"}

    def build_research_question(state: ResearchProjectState) -> dict[str, Any]:
        question = ResearchQuestion.model_validate(state["draft_research_question"])
        return {
            "active_stage": "save",
            "draft_research_question": question,
        }

    def save(state: ResearchProjectState) -> dict[str, Any]:
        question = ResearchQuestion.model_validate(state["draft_research_question"])
        record = repository.save_research_question(state["project_id"], question)
        return {
            "active_stage": "completed",
            "draft_research_question": None,
            "research_question_id": record.research_question_id,
        }

    builder = StateGraph(ResearchProjectState)
    builder.add_node("intake", intake)
    builder.add_node("build_research_question", build_research_question)
    builder.add_node("save", save)
    builder.add_edge(START, "intake")
    builder.add_edge("intake", "build_research_question")
    builder.add_edge("build_research_question", "save")
    builder.add_edge("save", END)
    return PersistentResearchProjectGraph(builder.compile(checkpointer=checkpointer))


@contextmanager
def open_research_project_graph(
    database_path: Path,
    checkpoint_path: Path,
) -> Iterator[PersistentResearchProjectGraph]:
    """Open a migrated Repository and a disk-backed SQLite Checkpointer."""

    resolved_checkpoint_path = checkpoint_path.expanduser().resolve()
    resolved_checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    upgrade_database(database_path)
    repository = ProjectRepository(database_path)
    try:
        with SqliteSaver.from_conn_string(str(resolved_checkpoint_path)) as checkpointer:
            yield build_research_project_graph(repository, checkpointer)
    finally:
        repository.close()


def _thread_config(thread_id: str) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": thread_id}}
