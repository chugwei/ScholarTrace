"""Auditable human approval workflow for a research-question draft."""

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from hashlib import sha256
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
from scholartrace.persistence.models import utc_now_naive
from scholartrace.persistence.repository import ProjectRepository
from scholartrace.schemas import DecisionRecord, ResearchQuestion
from scholartrace.states import ResearchProjectState

_QUESTION_FIELDS = {
    "problem",
    "target_population_or_domain",
    "inputs",
    "expected_outputs",
    "constraints",
    "success_criteria",
    "assumptions",
    "unresolved_questions",
}


class ResearchQuestionDecisionGraph:
    """Compiled graph facade with an explicit, thread-bound resume method."""

    def __init__(self, graph: Any) -> None:
        self.graph = graph

    def invoke(self, state: ResearchProjectState) -> dict[str, Any]:
        return cast(dict[str, Any], self.graph.invoke(state, _config(state["thread_id"])))

    def resume(self, thread_id: str, command: Command) -> dict[str, Any]:
        return cast(dict[str, Any], self.graph.invoke(command, _config(thread_id)))

    def get_state(self, thread_id: str) -> Any:
        return self.graph.get_state(_config(thread_id))


def build_research_question_decision_graph(
    repository: ProjectRepository,
    checkpointer: BaseCheckpointSaver[Any],
) -> ResearchQuestionDecisionGraph:
    """Build clarification → human decision → persist/loop workflow."""

    def intake(state: ResearchProjectState) -> dict[str, Any]:
        repository.create_project(
            project_id=state["project_id"],
            thread_id=state["thread_id"],
            current_goal=state["current_goal"],
        )
        payload = _payload_from_state(state)
        missing = find_missing_question_fields(payload)
        return {
            "active_stage": "awaiting_clarification" if missing else "awaiting_approval",
            "pending_questions": missing,
            "research_question_payload": payload,
        }

    def route_after_intake(state: ResearchProjectState) -> str:
        return "clarify" if state["pending_questions"] else "request_decision"

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
            "pending_questions": find_missing_question_fields(payload),
            "research_question_payload": payload,
        }

    def request_decision(state: ResearchProjectState) -> dict[str, Any]:
        decision = interrupt(
            {
                "kind": "research_question_decision",
                "target_type": "research_question",
                "target_id": _target_id(state),
                "payload": state["research_question_payload"],
                "actions": ["approved", "rejected", "modified", "cancelled", "paused"],
            }
        )
        if not isinstance(decision, Mapping):
            raise ValueError("decision resume value must be a mapping")
        return {"active_stage": "recording_decision", "pending_approval": dict(decision)}

    def apply_decision(state: ResearchProjectState) -> dict[str, Any]:
        raw_decision = state.get("pending_approval")
        if not isinstance(raw_decision, Mapping):
            raise ValueError("a pending human decision is required")
        record = _validated_record(state, raw_decision)
        updated_payload: dict[str, Any] | None = None
        if record.action == "modified":
            updated_payload = _modified_payload(state, record)
            # Validate before the workflow records and loops. A malformed
            # modification must never be presented as a reviewable question.
            ResearchQuestion.model_validate(updated_payload)
        repository.record_decision(
            decision_id=record.decision_id,
            project_id=record.project_id,
            thread_id=record.thread_id,
            target_type=record.target_type,
            target_id=record.target_id,
            action=record.action,
            actor_id=record.actor_id,
            reason=record.reason,
            payload=record.payload,
            created_at=record.created_at,
        )

        if record.action == "modified":
            repository.update_project_stage(state["project_id"], "awaiting_approval")
            return {
                "active_stage": "awaiting_approval",
                "pending_approval": None,
                "last_decision_action": "modified",
                "research_question_payload": updated_payload,
            }

        if record.action == "approved":
            return {
                "active_stage": "approved",
                "pending_approval": None,
                "last_decision_action": "approved",
            }

        repository.update_project_stage(state["project_id"], record.action)
        return {
            "active_stage": record.action,
            "pending_approval": None,
            "last_decision_action": record.action,
        }

    def route_after_decision(state: ResearchProjectState) -> str:
        action = state["last_decision_action"]
        if action == "approved":
            return "save"
        if action == "modified":
            return "request_decision"
        return "finish"

    def save(state: ResearchProjectState) -> dict[str, Any]:
        question = ResearchQuestion.model_validate(state["research_question_payload"])
        saved = repository.save_research_question(
            state["project_id"],
            question,
            active_stage="completed",
        )
        return {
            "active_stage": "completed",
            "draft_research_question": None,
            "research_question_id": saved.research_question_id,
        }

    def finish(_state: ResearchProjectState) -> dict[str, Any]:
        return {}

    builder = StateGraph(ResearchProjectState)
    builder.add_node("intake", intake)
    builder.add_node("clarify", clarify)
    builder.add_node("request_decision", request_decision)
    builder.add_node("apply_decision", apply_decision)
    builder.add_node("save", save)
    builder.add_node("finish", finish)
    builder.add_edge(START, "intake")
    builder.add_conditional_edges(
        "intake",
        route_after_intake,
        {"clarify": "clarify", "request_decision": "request_decision"},
    )
    builder.add_edge("clarify", "intake")
    builder.add_edge("request_decision", "apply_decision")
    builder.add_conditional_edges(
        "apply_decision",
        route_after_decision,
        {"save": "save", "request_decision": "request_decision", "finish": "finish"},
    )
    builder.add_edge("save", END)
    builder.add_edge("finish", END)
    return ResearchQuestionDecisionGraph(builder.compile(checkpointer=checkpointer))


@contextmanager
def open_research_question_decision_graph(
    database_path: Path,
    checkpoint_path: Path,
) -> Iterator[ResearchQuestionDecisionGraph]:
    """Open the decision workflow with disk-backed business/checkpoint stores."""

    resolved_checkpoint_path = checkpoint_path.expanduser().resolve()
    resolved_checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    upgrade_database(database_path)
    repository = ProjectRepository(database_path)
    try:
        with SqliteSaver.from_conn_string(str(resolved_checkpoint_path)) as checkpointer:
            yield build_research_question_decision_graph(repository, checkpointer)
    finally:
        repository.close()


def _validated_record(
    state: ResearchProjectState,
    raw_decision: Mapping[str, Any],
) -> DecisionRecord:
    payload = raw_decision.get("payload")
    if payload is None:
        payload = {}
    if not isinstance(payload, Mapping):
        raise ValueError("decision payload must be a mapping")
    fields = raw_decision.get("fields")
    if fields is not None:
        if not isinstance(fields, Mapping):
            raise ValueError("modified fields must be a mapping")
        payload = {**dict(payload), "fields": dict(fields)}
    return DecisionRecord.model_validate(
        {
            "decision_id": raw_decision.get("decision_id"),
            "project_id": state["project_id"],
            "thread_id": state["thread_id"],
            "target_type": "research_question",
            "target_id": _target_id(state),
            "action": raw_decision.get("action"),
            "actor_id": raw_decision.get("actor_id"),
            "reason": raw_decision.get("reason"),
            "payload": payload,
            "created_at": raw_decision.get("created_at") or utc_now_naive(),
        }
    )


def _modified_payload(
    state: ResearchProjectState,
    record: DecisionRecord,
) -> dict[str, Any]:
    fields = record.payload.get("fields", {})
    if not isinstance(fields, Mapping):
        raise ValueError("modified fields must be a mapping")
    unknown = set(fields) - _QUESTION_FIELDS
    if unknown:
        names = ", ".join(sorted(str(item) for item in unknown))
        raise ValueError(f"modified fields contain unknown names: {names}")
    payload = dict(state["research_question_payload"] or {})
    payload.update(fields)
    return payload


def _target_id(state: ResearchProjectState) -> str:
    existing = state.get("research_question_id")
    if existing:
        return existing
    digest = sha256(f"{state['project_id']}\0{state['thread_id']}".encode()).hexdigest()[:32]
    return f"rq_pending_{digest}"


def _config(thread_id: str) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": thread_id}}
