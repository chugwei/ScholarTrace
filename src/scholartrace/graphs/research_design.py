"""Human-gated research-design Subgraph for PipelineSpec and DataCollectionProtocol."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from typing import Any, cast

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from scholartrace.design.validation import DesignValidationError, validate_design_pair
from scholartrace.identifiers import validate_identifier
from scholartrace.persistence.design_repository import DesignRepository
from scholartrace.persistence.migrations import upgrade_database
from scholartrace.persistence.models import utc_now_naive
from scholartrace.persistence.repository import ProjectRepository
from scholartrace.schemas import DecisionRecord
from scholartrace.states import ResearchProjectState

_ACTIONS = {"approved", "rejected", "cancelled", "paused"}


class ResearchDesignGraph:
    """Compiled Subgraph facade bound to one persistent thread and two repositories."""

    def __init__(self, graph: Any, design_repository: DesignRepository) -> None:
        self.graph = graph
        self.design_repository = design_repository

    def invoke(self, state: ResearchProjectState) -> dict[str, Any]:
        thread_id = validate_identifier(state["thread_id"])
        return cast(dict[str, Any], self.graph.invoke(state, config=_config(thread_id)))

    def resume(self, thread_id: str, command: Command) -> dict[str, Any]:
        thread_id = validate_identifier(thread_id)
        return cast(dict[str, Any], self.graph.invoke(command, config=_config(thread_id)))

    def get_state(self, thread_id: str) -> dict[str, Any]:
        thread_id = validate_identifier(thread_id)
        snapshot = self.graph.get_state(_config(thread_id))
        if not snapshot.values:
            raise ResearchDesignGraphError(f"checkpoint for thread {thread_id!r} was not found")
        return cast(dict[str, Any], snapshot.values)


class ResearchDesignGraphError(RuntimeError):
    """Raised when a design graph checkpoint cannot be read."""


def build_research_design_graph(
    design_repository: DesignRepository,
    project_repository: ProjectRepository,
    checkpointer: BaseCheckpointSaver[Any],
) -> ResearchDesignGraph:
    """Build intake → draft persistence → interrupt approval → decision → END."""

    def intake(state: ResearchProjectState) -> dict[str, Any]:
        project_repository.create_project(
            project_id=state["project_id"],
            thread_id=state["thread_id"],
            current_goal=state["current_goal"],
        )
        if state.get("draft_pipeline_spec") is None or state.get("draft_data_protocol") is None:
            raise ValueError("both draft_pipeline_spec and draft_data_protocol are required")
        return {"active_stage": "persisting_design_drafts"}

    def persist_drafts(state: ResearchProjectState) -> dict[str, Any]:
        pipeline = design_repository.save_pipeline(cast(Any, state["draft_pipeline_spec"]))
        protocol = design_repository.save_protocol(cast(Any, state["draft_data_protocol"]))
        return {
            "active_stage": "awaiting_design_approval",
            "active_pipeline_id": pipeline.pipeline_id,
            "active_data_protocol_id": protocol.protocol_id,
            "draft_pipeline_spec": pipeline,
            "draft_data_protocol": protocol,
        }

    def request_approval(_state: ResearchProjectState) -> dict[str, Any]:
        decision = interrupt(
            {
                "kind": "research_design_approval",
                "target_type": "design",
                "actions": sorted(_ACTIONS),
                "requires_reason": True,
            }
        )
        if not isinstance(decision, Mapping):
            raise ValueError("design approval resume value must be a mapping")
        return {
            "active_stage": "recording_design_decision",
            "pending_design_approval": dict(decision),
        }

    def apply_decision(state: ResearchProjectState) -> dict[str, Any]:
        raw = state.get("pending_design_approval")
        if not isinstance(raw, Mapping):
            raise ValueError("a pending design decision is required")
        action = raw.get("action")
        actor_id = raw.get("actor_id")
        reason = raw.get("reason")
        if action not in _ACTIONS:
            raise ValueError("design action must be approved, rejected, cancelled, or paused")
        if not isinstance(actor_id, str):
            raise ValueError("design decision actor_id is required")
        actor_id = validate_identifier(actor_id)
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("design decision reason is required")
        pipeline_id = state.get("active_pipeline_id")
        protocol_id = state.get("active_data_protocol_id")
        if not pipeline_id or not protocol_id:
            raise ValueError("design IDs are required before approval")
        target_id = design_target_id(pipeline_id, protocol_id)
        validation_findings: list[dict[str, str]] = []
        if action == "approved":
            pipeline = design_repository.get_pipeline(state["project_id"], pipeline_id)
            protocol = design_repository.get_protocol(state["project_id"], protocol_id)
            report = validate_design_pair(pipeline, protocol)
            if not report.passed:
                raise DesignValidationError(report)
            validation_findings = [finding.model_dump() for finding in report.findings]
        decision_id = raw.get("decision_id") or _decision_id(
            state["project_id"], state["thread_id"], target_id, action, actor_id
        )
        record = DecisionRecord.model_validate(
            {
                "decision_id": decision_id,
                "project_id": state["project_id"],
                "thread_id": state["thread_id"],
                "target_type": "design",
                "target_id": target_id,
                "action": action,
                "actor_id": actor_id,
                "reason": reason.strip(),
                "payload": {
                    "pipeline_id": pipeline_id,
                    "protocol_id": protocol_id,
                    "validation_findings": validation_findings,
                },
                "created_at": raw.get("created_at") or utc_now_naive(),
            }
        )
        project_repository.record_decision(
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
        if action == "approved":
            design_repository.approve_design_pair(
                state["project_id"],
                pipeline_id,
                protocol_id,
                actor_id,
                reason.strip(),
            )
        elif action == "rejected":
            design_repository.reject_pipeline(
                state["project_id"], pipeline_id, actor_id, reason.strip()
            )
            design_repository.reject_protocol(
                state["project_id"], protocol_id, actor_id, reason.strip()
            )
        return {
            "active_stage": f"design_{action}",
            "pending_design_approval": None,
            "last_decision_action": action,
            "last_decision_actor": actor_id,
            "last_decision_id": record.decision_id,
        }

    def finish(_state: ResearchProjectState) -> dict[str, Any]:
        return {}

    builder = StateGraph(ResearchProjectState)
    builder.add_node("intake", intake)
    builder.add_node("persist_drafts", persist_drafts)
    builder.add_node("request_approval", request_approval)
    builder.add_node("apply_decision", apply_decision)
    builder.add_node("finish", finish)
    builder.add_edge(START, "intake")
    builder.add_edge("intake", "persist_drafts")
    builder.add_edge("persist_drafts", "request_approval")
    builder.add_edge("request_approval", "apply_decision")
    builder.add_edge("apply_decision", "finish")
    builder.add_edge("finish", END)
    return ResearchDesignGraph(
        builder.compile(checkpointer=checkpointer),
        design_repository,
    )


@contextmanager
def open_research_design_graph(
    database_path: Path,
    checkpoint_path: Path,
) -> Iterator[ResearchDesignGraph]:
    """Open the design Subgraph with SQLite business and checkpoint stores."""

    resolved_checkpoint_path = checkpoint_path.expanduser().resolve()
    resolved_checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    upgrade_database(database_path)
    design_repository = DesignRepository(database_path)
    project_repository = ProjectRepository(database_path)
    try:
        with SqliteSaver.from_conn_string(str(resolved_checkpoint_path)) as checkpointer:
            yield build_research_design_graph(
                design_repository,
                project_repository,
                checkpointer,
            )
    finally:
        design_repository.close()
        project_repository.close()


def design_target_id(pipeline_id: str, protocol_id: str) -> str:
    digest = sha256(f"{pipeline_id}\0{protocol_id}".encode()).hexdigest()[:32]
    return f"design_{digest}"


def _decision_id(
    project_id: str,
    thread_id: str,
    target_id: str,
    action: str,
    actor_id: str,
) -> str:
    digest = sha256(
        f"{project_id}\0{thread_id}\0{target_id}\0{action}\0{actor_id}".encode()
    ).hexdigest()[:32]
    return f"design_decision_{digest}"


def _config(thread_id: str) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": thread_id}}
