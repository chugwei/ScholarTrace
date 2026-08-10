from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from scholartrace.design.export import (
    DesignExportError,
    comparison_to_markdown,
    export_design_bundle,
)
from scholartrace.persistence.design_repository import DesignRepository
from scholartrace.persistence.migrations import upgrade_database
from scholartrace.persistence.repository import ProjectRepository
from scholartrace.schemas import (
    CaptureField,
    DataCollectionProtocol,
    PipelineSpec,
    PipelineStage,
    PipelineVersionComparison,
)


def pair() -> tuple[PipelineSpec, DataCollectionProtocol]:
    created_at = datetime(2026, 8, 11, tzinfo=UTC)
    return (
        PipelineSpec(
            pipeline_id="export-pipeline-v1",
            project_id="lychee-m5-export",
            version=1,
            title="荔枝病虫害导出管线",
            objective="Keep collection and evaluation traceable",
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
                    purpose="Evaluate held-out data",
                    inputs=["observations"],
                    outputs=["metrics"],
                ),
            ],
            evaluation_protocol="Group by orchard source",
            artifact_outputs=["manifest"],
            created_by="researcher-001",
            created_at=created_at,
        ),
        DataCollectionProtocol(
            protocol_id="export-protocol-v1",
            project_id="lychee-m5-export",
            version=1,
            title="荔枝采集协议",
            target_population="Synthetic orchard scenes",
            sampling_strategy="Group by orchard source",
            inclusion_criteria=["authorized scene"],
            capture_fields=[CaptureField(field_name="scene_id", description="Stable ID")],
            annotation_policy="Two-pass review",
            split_strategy="Group by orchard source",
            leakage_controls=["keep source groups separate"],
            consent_and_privacy="De-identified fixture only",
            created_by="researcher-001",
            created_at=created_at,
        ),
    )


def test_formal_export_requires_approved_designs_and_is_deterministic(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    projects = ProjectRepository(database_path)
    projects.create_project("lychee-m5-export", "lychee-m5-export")
    projects.close()
    pipeline, protocol = pair()
    with pytest.raises(DesignExportError, match="approved"):
        export_design_bundle(pipeline, protocol, tmp_path / "draft-export")

    repository = DesignRepository(database_path)
    saved_pipeline = repository.save_pipeline(pipeline)
    saved_protocol = repository.save_protocol(protocol)
    approved_pipeline, approved_protocol = repository.approve_design_pair(
        "lychee-m5-export",
        saved_pipeline.pipeline_id,
        saved_protocol.protocol_id,
        "researcher-001",
        "人工批准导出",
    )
    output_root = tmp_path / "formal-export"
    first = export_design_bundle(approved_pipeline, approved_protocol, output_root)
    first_bytes = {key: path.read_bytes() for key, path in first.items()}
    second = export_design_bundle(approved_pipeline, approved_protocol, output_root)
    assert {key: path.read_bytes() for key, path in second.items()} == first_bytes
    assert "荔枝病虫害导出管线" in first["pipeline_markdown"].read_text(encoding="utf-8")
    payload = yaml.safe_load(first["protocol_yaml"].read_text(encoding="utf-8"))
    assert payload["status"] == "approved"
    assert payload["content_sha256"] == approved_protocol.content_sha256
    repository.close()


def test_comparison_export_includes_changed_and_unchanged_sections() -> None:
    comparison = PipelineVersionComparison(
        project_id="lychee-m5-export",
        from_pipeline_id="export-pipeline-v1",
        to_pipeline_id="export-pipeline-v2",
        from_version=1,
        to_version=2,
        changed_fields=["stages"],
        added_stage_ids=["report"],
        removed_stage_ids=[],
    )
    markdown = comparison_to_markdown(comparison)
    assert "`stages`" in markdown
    assert "`report`" in markdown
    assert "## Removed stages" in markdown
