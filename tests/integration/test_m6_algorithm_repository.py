from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from scholartrace.algorithm import build_falsification_plan
from scholartrace.persistence.algorithm_repository import (
    AlgorithmDecisionConflictError,
    AlgorithmRepository,
    AlgorithmRepositoryError,
    AlgorithmVersionConflictError,
    PriorArtDecisionConflictError,
)
from scholartrace.persistence.database import create_sqlite_engine
from scholartrace.persistence.migrations import (
    LATEST_REVISION,
    current_revision,
    downgrade_database,
    upgrade_database,
)
from scholartrace.persistence.models import DocumentChunkRow, DocumentRow, EvidenceCardRow
from scholartrace.persistence.repository import ProjectRepository
from scholartrace.schemas import (
    AlgorithmComponent,
    AlgorithmSpec,
    InnovationCandidate,
    MethodDifference,
    PriorArtEntry,
    PriorArtMap,
)

CREATED_AT = datetime(2026, 8, 11, tzinfo=UTC)


def algorithm(
    *, project_id: str = "lychee-m6", version: int = 1, parent: str | None = None
) -> AlgorithmSpec:
    return AlgorithmSpec(
        algorithm_id=f"algo-v{version}",
        project_id=project_id,
        version=version,
        title="Occlusion-aware orchard detector",
        problem="Count visible fruit under canopy occlusion",
        task_type="object detection",
        inputs=["RGB orchard image"],
        outputs=["fruit boxes and confidence"],
        components=[
            AlgorithmComponent(
                component_id="backbone",
                name="visual backbone",
                role="extract image features",
                inputs=["RGB orchard image"],
                outputs=["feature pyramid"],
                rationale="preserve multi-scale fruit cues",
            ),
            AlgorithmComponent(
                component_id="occlusion-head",
                name="occlusion head",
                role="estimate visibility-aware boxes",
                inputs=["feature pyramid"],
                outputs=["fruit boxes and confidence"],
                rationale="make the proposed change testable",
            ),
        ],
        training_objective="optimize detection loss with an explicit visibility term",
        inference_strategy="run the same visibility-aware head at a fixed threshold",
        evaluation_protocol="evaluate on a source-grouped held-out split",
        pipeline_id="pipe-v1",
        protocol_id="protocol-v1",
        evidence_card_ids=["evidence-001"],
        assumptions=["the capture protocol records occlusion"],
        risks=["the visibility label may be noisy"],
        parent_algorithm_id=parent,
        created_by="researcher-001",
        created_at=CREATED_AT,
    )


def prior_art_map(*, project_id: str = "lychee-m6", algorithm_id: str = "algo-v1") -> PriorArtMap:
    return PriorArtMap(
        map_id="map-v1",
        project_id=project_id,
        algorithm_id=algorithm_id,
        version=1,
        entries=[
            PriorArtEntry(
                prior_art_entry_id="prior-art-001",
                title="Source-linked visibility baseline",
                evidence_card_ids=["evidence-001"],
                method_summary="Uses a standard detector with a visibility score",
                reported_strengths=["simple to reproduce"],
                reported_limitations=["does not separate capture-session effects"],
                applicability_notes="Relevant to the same orchard detection task",
            )
        ],
        unresolved_search_gaps=[],
        created_by="researcher-001",
        created_at=CREATED_AT,
    )


def candidate(
    *,
    candidate_id: str = "candidate-v1",
    version: int = 1,
    parent: str | None = None,
    extra_difference: bool = False,
) -> InnovationCandidate:
    differences = [
        MethodDifference(
            dimension="visibility supervision",
            prior_art_entry_id="prior-art-001",
            prior_art_approach="uses a single visibility score",
            proposed_approach="separates visibility from box regression",
            expected_effect="reduce errors under partial occlusion",
        )
    ]
    if extra_difference:
        differences.append(
            MethodDifference(
                dimension="split control",
                prior_art_entry_id="prior-art-001",
                prior_art_approach="random image split",
                proposed_approach="source-grouped split",
                expected_effect="reduce source leakage",
            )
        )
    return InnovationCandidate(
        candidate_id=candidate_id,
        project_id="lychee-m6",
        algorithm_id="algo-v1",
        prior_art_map_id="map-v1",
        version=version,
        title="Visibility-aware head candidate",
        problem="Count visible fruit under canopy occlusion",
        prior_art_entry_ids=["prior-art-001"],
        prior_art_evidence_ids=["evidence-001"],
        differences=differences,
        identified_gap="source grouping and visibility are not jointly tested",
        proposed_change="add a visibility-aware head and source-grouped evaluation",
        expected_mechanism="visibility supervision separates occluded and visible features",
        expected_benefit="fewer false negatives under occlusion",
        falsification_experiment="remove visibility supervision and compare held-out recall",
        required_baselines=["standard detector"],
        required_ablations=["without visibility head"],
        risks=["additional labels may be noisy"],
        parent_candidate_id=parent,
        created_by="researcher-001",
        created_at=CREATED_AT,
    )


def create_project(database_path: Path, project_id: str = "lychee-m6") -> None:
    repository = ProjectRepository(database_path)
    repository.create_project(project_id, project_id)
    repository.close()


def add_evidence_card(database_path: Path, project_id: str = "lychee-m6") -> None:
    engine = create_sqlite_engine(database_path)
    with Session(engine) as session, session.begin():
        session.add(
            DocumentRow(
                document_id="document-001",
                content_sha256="a" * 64,
                mime_type="text/plain",
                byte_size=10,
                source_type="manual",
                ingest_status="indexed",
                quality_status="ok",
                searchable=True,
                title="Authorized fixture evidence",
                authors=["Researcher"],
                created_at=CREATED_AT.replace(tzinfo=None),
            )
        )
        session.flush()
        session.add(
            DocumentChunkRow(
                chunk_id="chunk-001",
                document_id="document-001",
                ordinal=0,
                text="The baseline reports an occlusion score.",
                start_offset=0,
                end_offset=39,
                content_sha256="b" * 64,
                created_at=CREATED_AT.replace(tzinfo=None),
            )
        )
        session.add(
            EvidenceCardRow(
                evidence_card_id="evidence-001",
                project_id=project_id,
                document_id="document-001",
                chunk_id="chunk-001",
                statement="The baseline reports an occlusion score.",
                quote="The baseline reports an occlusion score.",
                source_start_offset=0,
                source_end_offset=39,
                locator_kind="local",
                locator_value="document-001",
                verification_status="verified",
                verified_by="researcher-001",
                created_at=CREATED_AT.replace(tzinfo=None),
            )
        )
    engine.dispose()


def test_m6_migration_rolls_back_algorithm_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    assert current_revision(database_path) == LATEST_REVISION


def test_m6_candidate_migration_rolls_back_candidate_table(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    assert current_revision(database_path) == "0010"
    downgrade_database(database_path, "0009")
    assert current_revision(database_path) == "0009"
    upgrade_database(database_path)
    assert current_revision(database_path) == LATEST_REVISION
    downgrade_database(database_path, "0008")
    assert current_revision(database_path) == "0008"
    upgrade_database(database_path)
    assert current_revision(database_path) == LATEST_REVISION


def test_algorithm_is_idempotent_and_approval_requires_resolved_evidence(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    create_project(database_path)
    repository = AlgorithmRepository(database_path)
    saved = repository.save_algorithm(algorithm())
    assert repository.save_algorithm(algorithm()) == saved
    with pytest.raises(AlgorithmDecisionConflictError, match="evidence cards"):
        repository.approve_algorithm("lychee-m6", "algo-v1", "researcher-001", "approve")
    add_evidence_card(database_path)
    approved = repository.approve_algorithm(
        "lychee-m6", "algo-v1", "researcher-001", "evidence checked"
    )
    assert approved.status == "approved"
    with pytest.raises(AlgorithmVersionConflictError, match="approved parent"):
        repository.save_algorithm(
            algorithm(version=2).model_copy(update={"title": "Occlusion-aware detector v2"})
        )
    second = repository.save_algorithm(
        algorithm(version=2, parent="algo-v1").model_copy(
            update={"title": "Occlusion-aware detector v2"}
        )
    )
    assert second.version == 2
    repository.close()


def test_prior_art_map_requires_approved_algorithm_and_evidence(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    create_project(database_path)
    add_evidence_card(database_path)
    repository = AlgorithmRepository(database_path)
    repository.save_algorithm(algorithm())
    saved_map = repository.save_prior_art_map(prior_art_map())
    with pytest.raises(PriorArtDecisionConflictError, match="approved algorithm"):
        repository.approve_prior_art_map("lychee-m6", saved_map.map_id, "researcher-001", "approve")
    repository.approve_algorithm("lychee-m6", "algo-v1", "researcher-001", "approved")
    approved_map = repository.approve_prior_art_map(
        "lychee-m6", saved_map.map_id, "researcher-001", "source checked"
    )
    assert approved_map.status == "approved"
    assert repository.get_prior_art_map("lychee-m6", "map-v1").status == "approved"
    repository.close()


def test_candidate_requires_map_references_and_has_deterministic_rank(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    create_project(database_path)
    add_evidence_card(database_path)
    repository = AlgorithmRepository(database_path)
    repository.save_algorithm(algorithm())
    repository.approve_algorithm("lychee-m6", "algo-v1", "researcher-001", "approved")
    repository.save_prior_art_map(prior_art_map())
    repository.approve_prior_art_map("lychee-m6", "map-v1", "researcher-001", "checked")

    saved = repository.save_candidate(candidate())
    assert repository.save_candidate(candidate()) == saved
    assert saved.status == "draft"
    assert saved.novelty_status == "unverified"
    with pytest.raises(AlgorithmRepositoryError, match="unknown prior-art entries"):
        repository.save_candidate(
            candidate(candidate_id="candidate-invalid").model_copy(
                update={"prior_art_entry_ids": ["missing-entry"]}
            )
        )

    second = repository.save_candidate(
        candidate(
            candidate_id="candidate-v2",
            version=2,
            parent="candidate-v1",
            extra_difference=True,
        ).model_copy(update={"title": "Visibility-aware head candidate v2"})
    )
    assert second.version == 2
    ranked = repository.rank_candidates("lychee-m6")
    assert ranked[0].candidate_id == "candidate-v2"
    assert ranked[0].score > ranked[1].score
    assert "does not establish novelty" in ranked[0].rationale[-1]
    repository.close()


def test_candidate_experiment_gate_requires_approved_sources_and_preserves_boundary(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    create_project(database_path)
    add_evidence_card(database_path)
    repository = AlgorithmRepository(database_path)
    repository.save_algorithm(algorithm())
    repository.save_prior_art_map(prior_art_map())
    repository.save_candidate(candidate())

    with pytest.raises(AlgorithmRepositoryError, match="algorithm specification must be approved"):
        repository.approve_candidate_for_experiment(
            "lychee-m6", "candidate-v1", "researcher-001", "enter validation"
        )
    repository.approve_algorithm("lychee-m6", "algo-v1", "researcher-001", "approved")
    with pytest.raises(AlgorithmRepositoryError, match="prior-art map must be approved"):
        repository.approve_candidate_for_experiment(
            "lychee-m6", "candidate-v1", "researcher-001", "enter validation"
        )
    repository.approve_prior_art_map("lychee-m6", "map-v1", "researcher-001", "checked")

    plan = build_falsification_plan(candidate())
    assert plan.status == "proposed"
    assert "frozen dataset split" in plan.evaluation_requirements[0]
    approved = repository.approve_candidate_for_experiment(
        "lychee-m6", "candidate-v1", "researcher-001", "allow validation only"
    )
    assert approved.status == "approved_for_experiment"
    assert approved.novelty_status == "unverified"
    withdrawn = repository.withdraw_candidate(
        "lychee-m6", "candidate-v1", "researcher-001", "new prior-art conflict"
    )
    assert withdrawn.status == "withdrawn"


def test_not_novel_candidate_is_blocked_and_draft_can_be_rejected(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    create_project(database_path)
    add_evidence_card(database_path)
    repository = AlgorithmRepository(database_path)
    repository.save_algorithm(algorithm())
    repository.approve_algorithm("lychee-m6", "algo-v1", "researcher-001", "approved")
    repository.save_prior_art_map(prior_art_map())
    repository.approve_prior_art_map("lychee-m6", "map-v1", "researcher-001", "checked")
    repository.save_candidate(
        candidate(candidate_id="candidate-not-novel").model_copy(
            update={"novelty_status": "not_novel"}
        )
    )
    with pytest.raises(AlgorithmRepositoryError, match="not_novel"):
        repository.approve_candidate_for_experiment(
            "lychee-m6", "candidate-not-novel", "researcher-001", "enter validation"
        )
    rejected = repository.reject_candidate(
        "lychee-m6", "candidate-not-novel", "researcher-001", "prior work already covers it"
    )
    assert rejected.status == "rejected"
    repository.close()


def test_algorithm_project_isolation_is_enforced(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    create_project(database_path, "lychee-m6")
    create_project(database_path, "orchard-m6")
    repository = AlgorithmRepository(database_path)
    repository.save_algorithm(algorithm())
    with pytest.raises(AlgorithmRepositoryError):
        repository.get_algorithm("orchard-m6", "algo-v1")
    repository.close()
