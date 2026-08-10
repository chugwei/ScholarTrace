from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import inspect

from scholartrace.persistence.database import create_sqlite_engine
from scholartrace.persistence.design_repository import (
    DesignDecisionConflictError,
    DesignNotFoundError,
    DesignRepository,
    DesignVersionConflictError,
)
from scholartrace.persistence.migrations import (
    LATEST_REVISION,
    current_revision,
    downgrade_database,
    upgrade_database,
)
from scholartrace.persistence.repository import ProjectRepository
from scholartrace.schemas import (
    CaptureField,
    DataCollectionProtocol,
    PipelineSpec,
    PipelineStage,
)

CREATED_AT = datetime(2026, 8, 11, tzinfo=UTC)


def create_project(database_path: Path, project_id: str = "lychee-m5") -> None:
    repository = ProjectRepository(database_path)
    repository.create_project(project_id, project_id)
    repository.close()


def pipeline(
    *,
    project_id: str = "lychee-m5",
    pipeline_id: str = "pipe-v1",
    version: int = 1,
    parent_pipeline_id: str | None = None,
    title: str = "Lychee disease detection pipeline",
) -> PipelineSpec:
    return PipelineSpec(
        pipeline_id=pipeline_id,
        project_id=project_id,
        version=version,
        title=title,
        objective="Evaluate a traceable agriculture-vision detection workflow",
        stages=[
            PipelineStage(
                stage_id="collect",
                name="Collect",
                purpose="Acquire authorized orchard observations",
                inputs=["sampling protocol"],
                outputs=["raw observations"],
                tools=["camera manifest"],
            ),
            PipelineStage(
                stage_id="evaluate",
                name="Evaluate",
                purpose="Measure held-out detection performance",
                inputs=["dataset version", "model checkpoint"],
                outputs=["metric result"],
                tools=["evaluation script"],
            ),
        ],
        evaluation_protocol="Use a project-scoped held-out split with fixed thresholds",
        artifact_outputs=["dataset manifest", "evaluation report"],
        assumptions=["authorization is still to be confirmed"],
        risks=["background leakage"],
        parent_pipeline_id=parent_pipeline_id,
        created_by="researcher-001",
        created_at=CREATED_AT,
    )


def protocol(
    *,
    project_id: str = "lychee-m5",
    protocol_id: str = "protocol-v1",
    version: int = 1,
    parent_protocol_id: str | None = None,
) -> DataCollectionProtocol:
    return DataCollectionProtocol(
        protocol_id=protocol_id,
        project_id=project_id,
        version=version,
        title="Lychee orchard observation protocol",
        target_population="Synthetic de-identified orchard scenes",
        sampling_strategy="Stratify by canopy, occlusion and lighting condition",
        inclusion_criteria=["authorized scene description"],
        exclusion_criteria=["duplicate observation"],
        capture_fields=[
            CaptureField(field_name="scene_id", description="Stable scene identifier"),
            CaptureField(field_name="weather", description="Weather category", required=False),
        ],
        annotation_policy="Two-pass review with an adjudication record",
        split_strategy="Group by orchard and capture session before train/test split",
        leakage_controls=["no scene identity across train and test"],
        consent_and_privacy="Use only authorized and de-identified material",
        parent_protocol_id=parent_protocol_id,
        created_by="researcher-001",
        created_at=CREATED_AT,
    )


def test_m5_migration_can_roll_back_design_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    assert current_revision(database_path) == LATEST_REVISION
    engine = create_sqlite_engine(database_path)
    tables = set(inspect(engine).get_table_names())
    assert {"pipeline_specs", "data_collection_protocols"} <= tables
    engine.dispose()

    downgrade_database(database_path, "0007")
    assert current_revision(database_path) == "0007"
    engine = create_sqlite_engine(database_path)
    tables = set(inspect(engine).get_table_names())
    assert not {"pipeline_specs", "data_collection_protocols"} & tables
    engine.dispose()
    upgrade_database(database_path)
    assert current_revision(database_path) == LATEST_REVISION


def test_pipeline_versions_are_idempotent_and_need_explicit_approval_parent(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    create_project(database_path)
    repository = DesignRepository(database_path)

    first = repository.save_pipeline(pipeline())
    replay = repository.save_pipeline(pipeline())
    assert replay == first
    assert first.status == "draft"
    assert first.content_sha256 is not None

    approved = repository.approve_pipeline(
        "lychee-m5", "pipe-v1", "researcher-001", "黄金样例管线结构完整"
    )
    assert approved.status == "approved"
    assert approved.approved_by == "researcher-001"

    with pytest.raises(DesignVersionConflictError, match="approved parent"):
        repository.save_pipeline(
            pipeline(
                pipeline_id="pipe-v2",
                version=2,
                title="Lychee disease pipeline without explicit parent",
            )
        )

    second = repository.save_pipeline(
        pipeline(
            pipeline_id="pipe-v2",
            version=2,
            parent_pipeline_id="pipe-v1",
            title="Lychee disease pipeline with occlusion checks",
        )
    )
    assert second.version == 2
    approved_second = repository.approve_pipeline(
        "lychee-m5", "pipe-v2", "researcher-001", "增加遮挡分层评估"
    )
    assert approved_second.status == "approved"
    assert repository.get_pipeline("lychee-m5", "pipe-v1").status == "superseded"
    assert [item.version for item in repository.list_pipelines("lychee-m5")] == [1, 2]
    repository.close()


def test_protocol_approval_rejection_and_project_isolation(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    create_project(database_path, "lychee-m5")
    create_project(database_path, "orchard-m5")
    repository = DesignRepository(database_path)

    saved = repository.save_protocol(protocol())
    rejected = repository.reject_protocol(
        "lychee-m5", saved.protocol_id, "researcher-001", "采集授权范围仍未确认"
    )
    assert rejected.status == "rejected"
    assert "授权" in (rejected.decision_reason or "")
    with pytest.raises(DesignDecisionConflictError, match="only draft"):
        repository.approve_protocol("lychee-m5", saved.protocol_id, "researcher-001", "late")

    isolated = repository.save_protocol(
        protocol(project_id="orchard-m5", protocol_id="orchard-protocol-v1")
    )
    assert repository.get_protocol("orchard-m5", isolated.protocol_id).project_id == "orchard-m5"
    with pytest.raises(DesignNotFoundError):
        repository.get_protocol("lychee-m5", isolated.protocol_id)
    repository.close()


def test_design_contracts_reject_duplicate_graph_or_capture_names() -> None:
    duplicate_stage = pipeline().model_copy(
        update={
            "stages": [
                pipeline().stages[0],
                pipeline().stages[0].model_copy(update={"name": "Other"}),
            ]
        }
    )
    with pytest.raises(ValueError, match="stage_id"):
        PipelineSpec.model_validate(duplicate_stage.model_dump())

    with pytest.raises(ValueError, match="capture field_name"):
        DataCollectionProtocol(
            **protocol().model_dump(exclude={"capture_fields"}),
            capture_fields=[
                CaptureField(field_name="scene_id", description="one"),
                CaptureField(field_name="scene_id", description="two"),
            ],
        )
