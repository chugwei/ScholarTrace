"""State contract for the persistent research-project graph."""

from collections.abc import Iterable
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

from scholartrace.identifiers import validate_identifier
from scholartrace.schemas.research import ResearchQuestion


def merge_unique_strings(left: Iterable[str], right: Iterable[str]) -> list[str]:
    """Merge strings in first-seen order without mutating either input."""

    return list(dict.fromkeys([*left, *right]))


def replace_strings(_left: Iterable[str], right: Iterable[str]) -> list[str]:
    """Replace a current string list with an ordered, duplicate-free update."""

    return list(dict.fromkeys(right))


class ResearchProjectState(TypedDict):
    """Small, replay-safe workflow state containing references, not large artifacts."""

    messages: Annotated[list[AnyMessage], add_messages]

    project_id: str
    thread_id: str
    active_stage: str
    current_goal: str | None
    pending_questions: Annotated[list[str], replace_strings]
    pending_approval: dict[str, Any] | None

    research_question_id: str | None
    draft_research_question: ResearchQuestion | None
    research_question_payload: dict[str, Any] | None
    approved_document_ids: Annotated[list[str], merge_unique_strings]
    evidence_ids: Annotated[list[str], merge_unique_strings]
    claim_ids: Annotated[list[str], merge_unique_strings]

    active_pipeline_id: str | None
    active_data_protocol_id: str | None
    active_algorithm_id: str | None
    active_experiment_plan_id: str | None
    active_run_ids: Annotated[list[str], merge_unique_strings]

    manuscript_id: str | None
    artifact_ids: Annotated[list[str], merge_unique_strings]
    deployment_package_id: str | None

    next_actions: Annotated[list[str], merge_unique_strings]
    warnings: Annotated[list[str], merge_unique_strings]


def new_research_project_state(
    project_id: str,
    thread_id: str,
    current_goal: str | None = None,
) -> ResearchProjectState:
    """Create an isolated initial state for a new persistent project run."""

    return ResearchProjectState(
        messages=[],
        project_id=validate_identifier(project_id),
        thread_id=validate_identifier(thread_id),
        active_stage="intake",
        current_goal=current_goal,
        pending_questions=[],
        pending_approval=None,
        research_question_id=None,
        draft_research_question=None,
        research_question_payload=None,
        approved_document_ids=[],
        evidence_ids=[],
        claim_ids=[],
        active_pipeline_id=None,
        active_data_protocol_id=None,
        active_algorithm_id=None,
        active_experiment_plan_id=None,
        active_run_ids=[],
        manuscript_id=None,
        artifact_ids=[],
        deployment_package_id=None,
        next_actions=[],
        warnings=[],
    )
