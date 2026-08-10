from datetime import UTC, datetime
from pathlib import Path

import pytest

from scholartrace.design.validation import (
    DesignValidationError,
    compare_pipeline_versions,
    validate_data_collection_protocol,
    validate_design_pair,
    validate_pipeline_spec,
)
from scholartrace.persistence.design_repository import DesignRepository
from scholartrace.persistence.migrations import upgrade_database
from scholartrace.persistence.repository import ProjectRepository
from scholartrace.schemas import (
    CaptureField,
    DataCollectionProtocol,
    PipelineSpec,
    PipelineStage,
)


def pipeline(*, project_id: str = "lychee-m5-quality", version: int = 1) -> PipelineSpec:
    return PipelineSpec(
        pipeline_id=f"quality-pipeline-v{version}",
        project_id=project_id,
        version=version,
        title="Quality pipeline",
        objective="Connect collection to evaluation",
        stages=[
            PipelineStage(
                stage_id="collect",
                name="Collect",
                purpose="Collect observations",
                inputs=["protocol"],
                outputs=["observations"],
            ),
            PipelineStage(
                stage_id="evaluate",
                name="Evaluate",
                purpose="Evaluate held-out data",
                inputs=["observations"],
                outputs=["metrics"],
            ),
        ],
        evaluation_protocol="Group by source before evaluation",
        artifact_outputs=["manifest"],
        created_by="researcher-001",
        created_at=datetime(2026, 8, 11, tzinfo=UTC),
    )


def protocol(*, project_id: str = "lychee-m5-quality") -> DataCollectionProtocol:
    return DataCollectionProtocol(
        protocol_id="quality-protocol-v1",
        project_id=project_id,
        version=1,
        title="Quality protocol",
        target_population="Synthetic orchard scenes",
        sampling_strategy="Group by orchard source",
        inclusion_criteria=["authorized scene"],
        capture_fields=[CaptureField(field_name="scene_id", description="Stable ID")],
        annotation_policy="Two-pass review",
        split_strategy="Group by orchard source",
        leakage_controls=["keep source groups separate"],
        consent_and_privacy="De-identified fixture only",
        created_by="researcher-001",
        created_at=datetime(2026, 8, 11, tzinfo=UTC),
    )


def test_quality_and_leakage_report_passes_the_agriculture_fixture() -> None:
    report = validate_design_pair(pipeline(), protocol())
    assert report.passed is True
    assert report.findings == []


def test_disconnected_pipeline_and_random_split_are_blocking_findings() -> None:
    disconnected = pipeline().model_copy(
        update={
            "stages": [
                pipeline().stages[0],
                pipeline().stages[1].model_copy(update={"inputs": ["unrelated input"]}),
            ]
        }
    )
    disconnected = PipelineSpec.model_validate(disconnected.model_dump())
    pipeline_report = validate_pipeline_spec(disconnected)
    assert pipeline_report.passed is False
    assert pipeline_report.findings[0].code == "pipeline.disconnected_stage"

    unsafe = protocol().model_copy(
        update={"split_strategy": "random row split", "leakage_controls": ["review labels"]}
    )
    unsafe = DataCollectionProtocol.model_validate(unsafe.model_dump())
    protocol_report = validate_data_collection_protocol(unsafe)
    assert protocol_report.passed is False
    assert {finding.code for finding in protocol_report.findings} == {
        "protocol.split_leakage_risk",
        "protocol.leakage_control_missing",
    }


def test_pipeline_version_comparison_reports_stage_and_field_changes() -> None:
    before = pipeline()
    after = PipelineSpec.model_validate(
        before.model_copy(
            update={
                "pipeline_id": "quality-pipeline-v2",
                "version": 2,
                "title": "Quality pipeline with review",
                "stages": [
                    *before.stages,
                    PipelineStage(
                        stage_id="report",
                        name="Report",
                        purpose="Publish traceable report",
                        inputs=["metrics"],
                        outputs=["report"],
                    ),
                ],
            }
        ).model_dump()
    )
    comparison = compare_pipeline_versions(before, after)
    assert comparison.changed_fields == ["stages", "title"]
    assert comparison.added_stage_ids == ["report"]
    assert comparison.removed_stage_ids == []


def test_approval_gate_keeps_invalid_designs_as_drafts(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    projects = ProjectRepository(database_path)
    projects.create_project("lychee-m5-quality", "lychee-m5-quality")
    projects.close()
    repository = DesignRepository(database_path)
    invalid_protocol = DataCollectionProtocol.model_validate(
        protocol()
        .model_copy(update={"split_strategy": "random rows", "leakage_controls": ["review labels"]})
        .model_dump()
    )
    saved_pipeline = repository.save_pipeline(pipeline())
    saved_protocol = repository.save_protocol(invalid_protocol)
    with pytest.raises(DesignValidationError, match="grouping"):
        repository.approve_design_pair(
            "lychee-m5-quality",
            saved_pipeline.pipeline_id,
            saved_protocol.protocol_id,
            "researcher-001",
            "attempted approval",
        )
    assert (
        repository.get_pipeline("lychee-m5-quality", saved_pipeline.pipeline_id).status == "draft"
    )
    assert (
        repository.get_protocol("lychee-m5-quality", saved_protocol.protocol_id).status == "draft"
    )
    repository.close()
