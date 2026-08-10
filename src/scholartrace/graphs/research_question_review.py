"""M2.1 missing-information routing for research-question intake."""

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from scholartrace.graphs.research_project import PersistentResearchProjectGraph
from scholartrace.persistence.migrations import upgrade_database
from scholartrace.persistence.repository import ProjectRepository
from scholartrace.schemas import ResearchQuestion
from scholartrace.states import ResearchProjectState

_QUESTION_FIELDS = (
    "problem",
    "target_population_or_domain",
    "inputs",
    "expected_outputs",
    "constraints",
    "success_criteria",
    "assumptions",
    "unresolved_questions",
)
_CORE_LIST_FIELDS = {"inputs", "expected_outputs", "success_criteria"}
_TEXT_FIELDS = {"problem", "target_population_or_domain"}


def find_missing_question_fields(payload: Mapping[str, Any] | None) -> list[str]:
    """Return missing fields in contract order without inventing their values."""

    if payload is None:
        return list(_QUESTION_FIELDS)

    missing: list[str] = []
    for field in _QUESTION_FIELDS:
        if field not in payload:
            missing.append(field)
            continue
        value = payload[field]
        if field in _TEXT_FIELDS:
            if not isinstance(value, str) or not value.strip():
                missing.append(field)
            continue
        if not isinstance(value, list):
            missing.append(field)
            continue
        if field in _CORE_LIST_FIELDS and not any(
            isinstance(item, str) and item.strip() for item in value
        ):
            missing.append(field)
    return missing


def _payload_from_state(state: ResearchProjectState) -> dict[str, Any] | None:
    payload = state.get("research_question_payload")
    if payload is not None:
        return cast(dict[str, Any], payload)
    draft = state.get("draft_research_question")
    if isinstance(draft, ResearchQuestion):
        return draft.model_dump(mode="json")
    if isinstance(draft, dict):
        return draft
    return None


def build_research_question_review_graph(
    repository: ProjectRepository,
    checkpointer: BaseCheckpointSaver[Any],
) -> PersistentResearchProjectGraph:
    """Build M2.1 intake with a deterministic Conditional Edge."""

    def intake(state: ResearchProjectState) -> dict[str, Any]:
        repository.create_project(
            project_id=state["project_id"],
            thread_id=state["thread_id"],
            current_goal=state["current_goal"],
        )
        payload = _payload_from_state(state)
        return {
            "active_stage": "intake",
            "pending_questions": find_missing_question_fields(payload),
            "research_question_payload": payload,
        }

    def route_after_intake(state: ResearchProjectState) -> str:
        if state["pending_questions"]:
            return "clarify"
        return "build_research_question"

    def clarify(_state: ResearchProjectState) -> dict[str, Any]:
        return {
            "active_stage": "awaiting_clarification",
            "next_actions": ["provide_missing_research_question_fields"],
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
    builder.add_edge("clarify", END)
    builder.add_edge("build_research_question", "save")
    builder.add_edge("save", END)
    return PersistentResearchProjectGraph(builder.compile(checkpointer=checkpointer))


@contextmanager
def open_research_question_review_graph(
    database_path: Path,
    checkpoint_path: Path,
) -> Iterator[PersistentResearchProjectGraph]:
    """Open M2.1 review graph with migrated business and checkpoint stores."""

    resolved_checkpoint_path = checkpoint_path.expanduser().resolve()
    resolved_checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    upgrade_database(database_path)
    repository = ProjectRepository(database_path)
    try:
        with SqliteSaver.from_conn_string(str(resolved_checkpoint_path)) as checkpointer:
            yield build_research_question_review_graph(repository, checkpointer)
    finally:
        repository.close()
