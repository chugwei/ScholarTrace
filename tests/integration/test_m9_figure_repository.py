import csv
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from scholartrace.figures import (
    FigureRenderer,
    FigureRenderError,
    build_caption,
    recommend_figure_types,
    validate_bundle_numeric_consistency,
)
from scholartrace.persistence.database import create_sqlite_engine
from scholartrace.persistence.figure_repository import (
    FigureDecisionConflictError,
    FigureRepository,
    FigureRepositoryError,
)
from scholartrace.persistence.migrations import (
    LATEST_REVISION,
    current_revision,
    downgrade_database,
    upgrade_database,
)
from scholartrace.persistence.models import (
    AlgorithmSpecRow,
    ExperimentPlanRow,
    MetricResultRow,
    RunManifestRow,
)
from scholartrace.persistence.repository import ProjectRepository
from scholartrace.schemas import FigurePoint, FigureSpec, MetricResult

CREATED_AT = datetime(2026, 8, 11, tzinfo=UTC)


def setup_database(database_path: Path, *, verified: bool = True) -> None:
    upgrade_database(database_path)
    project = ProjectRepository(database_path)
    project.create_project("lychee-m9", "lychee-m9")
    project.close()
    engine = create_sqlite_engine(database_path)
    with Session(engine) as session, session.begin():
        session.add(
            AlgorithmSpecRow(
                algorithm_id="algo-m9",
                project_id="lychee-m9",
                version=1,
                content_sha256="a" * 64,
                payload={},
                status="approved",
                created_by="researcher-001",
                created_at=CREATED_AT.replace(tzinfo=None),
            )
        )
        session.flush()
        session.add(
            ExperimentPlanRow(
                plan_id="plan-m9",
                project_id="lychee-m9",
                algorithm_id="algo-m9",
                version=1,
                content_sha256="b" * 64,
                payload={"matrix": [], "data_version": "sha256:data-v1"},
                status="frozen",
                created_by="researcher-001",
                created_at=CREATED_AT.replace(tzinfo=None),
            )
        )
        session.flush()
        session.add(
            RunManifestRow(
                run_id="run-m9",
                project_id="lychee-m9",
                plan_id="plan-m9",
                matrix_entry_id="matrix-m9",
                status="validated",
                payload={},
                created_at=CREATED_AT.replace(tzinfo=None),
            )
        )
        session.flush()
        session.add(
            MetricResultRow(
                metric_result_id="metric-m9",
                project_id="lychee-m9",
                run_id="run-m9",
                name="accuracy",
                split="validation",
                value=0.9,
                source="independent_recompute",
                verification_status="verified" if verified else "unverifiable",
                is_final=verified,
                payload={"data_version": "sha256:data-v1"},
                created_at=CREATED_AT.replace(tzinfo=None),
            )
        )
    engine.dispose()


def spec(*, figure_id: str = "figure-m9") -> FigureSpec:
    return FigureSpec(
        figure_id=figure_id,
        project_id="lychee-m9",
        title="Validation accuracy",
        kind="bar",
        x_label="method",
        y_label="accuracy",
        points=[FigurePoint(label="proposed", value=0.9, metric_result_id="metric-m9")],
        metric_result_ids=["metric-m9"],
        data_version="sha256:data-v1",
        caption="Validation accuracy from the verified metric result.",
        created_by="researcher-001",
        created_at=CREATED_AT,
    )


def test_figure_migration_rolls_back(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    assert current_revision(database_path) == LATEST_REVISION
    downgrade_database(database_path, "0016")
    assert current_revision(database_path) == "0016"
    upgrade_database(database_path)
    assert current_revision(database_path) == LATEST_REVISION


def test_figure_spec_requires_verified_metric_and_approval(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    setup_database(database_path)
    repository = FigureRepository(database_path)
    saved = repository.save_spec(spec())
    assert saved.status == "draft"
    assert len(saved.content_sha256 or "") == 64
    assert repository.save_spec(spec()) == saved
    approved = repository.approve_spec(
        "lychee-m9",
        "figure-m9",
        actor_id="researcher-001",
        reason="verified metric and explicit caption",
    )
    assert approved.status == "approved"
    with pytest.raises(FigureDecisionConflictError, match="only draft"):
        repository.approve_spec(
            "lychee-m9",
            "figure-m9",
            actor_id="researcher-001",
            reason="duplicate approval",
        )
    repository.close()


def test_figure_rejects_unverified_and_mismatched_metric_data(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    setup_database(database_path, verified=False)
    repository = FigureRepository(database_path)
    with pytest.raises(FigureRepositoryError, match="verified final"):
        repository.save_spec(spec())
    repository.close()

    other_database = tmp_path / "other.db"
    setup_database(other_database)
    repository = FigureRepository(other_database)
    with pytest.raises(FigureRepositoryError, match="data_version"):
        repository.save_spec(spec().model_copy(update={"data_version": "sha256:wrong"}))
    repository.close()


def test_approved_figure_renders_rebuildable_artifact_bundle(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    setup_database(database_path)
    repository = FigureRepository(database_path)
    repository.save_spec(spec())
    approved = repository.approve_spec(
        "lychee-m9",
        "figure-m9",
        actor_id="researcher-001",
        reason="render the verified validation metric",
    )
    renderer = FigureRenderer()
    output_root = tmp_path / "artifacts"
    bundle = renderer.render(approved, output_root)
    bundle_root = output_root / "figure-m9"
    assert bundle.bundle_relpath == "figure-m9"
    assert bundle.output_relpaths == {
        "png": "figure-m9/figure.png",
        "svg": "figure-m9/figure.svg",
        "pdf": "figure-m9/figure.pdf",
    }
    for name in (
        "figure-spec.yaml",
        "input-data.csv",
        "generate_figure.py",
        "figure.png",
        "figure.svg",
        "figure.pdf",
        "caption.md",
        "provenance.json",
    ):
        assert (bundle_root / name).is_file()
        assert (bundle_root / name).stat().st_size > 0
    with (bundle_root / "input-data.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows == [
        {"label": "proposed", "value": "0.90000000000000002", "metric_result_id": "metric-m9"}
    ]
    provenance = json.loads((bundle_root / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["metric_result_ids"] == ["metric-m9"]
    data_hash = bundle.data_sha256
    for extension in approved.output_formats:
        (bundle_root / f"figure.{extension}").unlink()
    renderer.rebuild_from_script(bundle_root)
    assert all(
        (bundle_root / f"figure.{extension}").is_file() for extension in approved.output_formats
    )
    assert bundle.data_sha256 == data_hash
    repository.close()


def test_renderer_requires_approval_and_rejects_unsupported_kind(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    setup_database(database_path)
    repository = FigureRepository(database_path)
    draft = repository.save_spec(spec())
    with pytest.raises(FigureRenderError, match="approved"):
        FigureRenderer().render(draft, tmp_path / "artifacts")
    approved = repository.approve_spec(
        "lychee-m9",
        "figure-m9",
        actor_id="researcher-001",
        reason="test renderer gate",
    )
    unsupported = approved.model_copy(update={"kind": "confusion_matrix"})
    with pytest.raises(FigureRenderError, match="not supported"):
        FigureRenderer().render(unsupported, tmp_path / "unsupported")
    repository.close()


def metric(*, value: float = 0.9, verified: bool = True) -> MetricResult:
    return MetricResult(
        metric_result_id="metric-m9",
        project_id="lychee-m9",
        run_id="run-m9",
        name="accuracy",
        split="validation",
        value=value,
        source="independent_recompute",
        verification_status="verified" if verified else "unverifiable",
        is_final=verified,
        data_version="sha256:data-v1",
        evaluation_script_sha256="e" * 64,
        created_at=CREATED_AT,
    )


def test_figure_caption_suggestions_and_numeric_provenance_checks(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    setup_database(database_path)
    repository = FigureRepository(database_path)
    repository.save_spec(spec())
    approved = repository.approve_spec(
        "lychee-m9",
        "figure-m9",
        actor_id="researcher-001",
        reason="numeric validation",
    )
    bundle_root = tmp_path / "artifacts"
    bundle = FigureRenderer().render(approved, bundle_root)
    verified = metric()
    report = validate_bundle_numeric_consistency(
        approved,
        bundle,
        bundle_root / "figure-m9",
        [verified],
    )
    assert report.numeric_status == "passed"
    assert report.provenance_status == "passed"
    assert recommend_figure_types([verified])[0].kind == "bar"
    assert recommend_figure_types([metric(verified=False)]) == []
    assert "metric-m9" in build_caption(approved, [verified])
    with pytest.raises(ValueError, match="verified final"):
        build_caption(approved, [metric(verified=False)])
    (bundle_root / "figure-m9" / "input-data.csv").write_text(
        "label,value,metric_result_id\nproposed,0.8,metric-m9\n",
        encoding="utf-8",
    )
    failed = validate_bundle_numeric_consistency(
        approved,
        bundle,
        bundle_root / "figure-m9",
        [verified],
    )
    assert failed.numeric_status == "failed"
    repository.close()
