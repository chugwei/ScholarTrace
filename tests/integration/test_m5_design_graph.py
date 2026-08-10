from datetime import UTC, datetime
from pathlib import Path

import pytest
from langgraph.types import Command

from scholartrace.design import pipeline_to_mermaid
from scholartrace.graphs.research_design import open_research_design_graph
from scholartrace.persistence.design_repository import DesignRepository
from scholartrace.persistence.repository import ProjectRepository
from scholartrace.schemas import (
    CaptureField,
    DataCollectionProtocol,
    PipelineSpec,
    PipelineStage,
)
from scholartrace.states import new_research_project_state


def design_pair(project_id: str = "lychee-m5-graph") -> tuple[PipelineSpec, DataCollectionProtocol]:
    created_at = datetime(2026, 8, 11, tzinfo=UTC)
    pipeline = PipelineSpec(
        pipeline_id="pipe-graph-v1",
        project_id=project_id,
        version=1,
        title="Graph pipeline",
        objective="Trace collection and evaluation",
        stages=[
            PipelineStage(
                stage_id="collect",
                name="Collect",
                purpose="Collect authorized observations",
                inputs=["protocol"],
                outputs=["observations"],
            ),
            PipelineStage(
                stage_id="evaluate",
                name="Evaluate",
                purpose="Evaluate a held-out split",
                inputs=["observations"],
                outputs=["metrics"],
            ),
        ],
        evaluation_protocol="Fixed held-out split",
        artifact_outputs=["manifest"],
        created_by="researcher-001",
        created_at=created_at,
    )
    protocol = DataCollectionProtocol(
        protocol_id="protocol-graph-v1",
        project_id=project_id,
        version=1,
        title="Graph collection protocol",
        target_population="Synthetic orchard scenes",
        sampling_strategy="Stratify by occlusion",
        inclusion_criteria=["authorized scene"],
        capture_fields=[CaptureField(field_name="scene_id", description="Stable ID")],
        annotation_policy="Two-pass review",
        split_strategy="Group by scene source",
        leakage_controls=["no source group overlap"],
        consent_and_privacy="De-identified fixture only",
        created_by="researcher-001",
        created_at=created_at,
    )
    return pipeline, protocol


def test_design_subgraph_interrupt_resume_approves_both_designs_and_audits(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "domain.db"
    checkpoint_path = tmp_path / "checkpoints.db"
    pipeline, protocol = design_pair()
    state = new_research_project_state("lychee-m5-graph", "lychee-m5-graph")
    state["draft_pipeline_spec"] = pipeline
    state["draft_data_protocol"] = protocol

    with open_research_design_graph(database_path, checkpoint_path) as graph:
        paused = graph.invoke(state)
        assert paused["active_stage"] == "awaiting_design_approval"
        assert paused["active_pipeline_id"] == pipeline.pipeline_id
        assert graph.get_state("lychee-m5-graph")["pending_design_approval"] is None
        resumed = graph.resume(
            "lychee-m5-graph",
            Command(
                resume={
                    "action": "approved",
                    "actor_id": "researcher-001",
                    "reason": "黄金样例设计边界清晰",
                }
            ),
        )
        assert resumed["active_stage"] == "design_approved"
        assert resumed["pending_design_approval"] is None

    design_repository = DesignRepository(database_path)
    project_repository = ProjectRepository(database_path)
    assert (
        design_repository.get_pipeline("lychee-m5-graph", pipeline.pipeline_id).status == "approved"
    )
    assert (
        design_repository.get_protocol("lychee-m5-graph", protocol.protocol_id).status == "approved"
    )
    decisions = project_repository.list_decisions("lychee-m5-graph", target_type="design")
    assert len(decisions) == 1
    assert decisions[0].action == "approved"
    design_repository.close()
    project_repository.close()


def test_design_subgraph_rejects_without_promoting_drafts(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    checkpoint_path = tmp_path / "checkpoints.db"
    pipeline, protocol = design_pair("lychee-m5-reject")
    state = new_research_project_state("lychee-m5-reject", "lychee-m5-reject")
    state["draft_pipeline_spec"] = pipeline
    state["draft_data_protocol"] = protocol

    with open_research_design_graph(database_path, checkpoint_path) as graph:
        graph.invoke(state)
        result = graph.resume(
            "lychee-m5-reject",
            Command(
                resume={
                    "action": "rejected",
                    "actor_id": "researcher-001",
                    "reason": "采集授权仍然缺失",
                }
            ),
        )
        assert result["active_stage"] == "design_rejected"

    repository = DesignRepository(database_path)
    assert repository.get_pipeline("lychee-m5-reject", pipeline.pipeline_id).status == "rejected"
    assert repository.get_protocol("lychee-m5-reject", protocol.protocol_id).status == "rejected"
    repository.close()


def test_design_subgraph_requires_both_drafts_and_mermaid_is_deterministic(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    checkpoint_path = tmp_path / "checkpoints.db"
    pipeline, _ = design_pair("lychee-m5-invalid")
    state = new_research_project_state("lychee-m5-invalid", "lychee-m5-invalid")
    state["draft_pipeline_spec"] = pipeline
    with (
        open_research_design_graph(database_path, checkpoint_path) as graph,
        pytest.raises(ValueError, match="both draft"),
    ):
        graph.invoke(state)

    rendered = pipeline_to_mermaid(pipeline)
    assert rendered.splitlines()[0] == "flowchart LR"
    assert 'stage_0["Collect (collect)"]' in rendered
    assert "stage_0 --> stage_1" in rendered
