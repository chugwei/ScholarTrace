from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from scholartrace.persistence.database import create_sqlite_engine
from scholartrace.persistence.manuscript_repository import (
    ClaimEvidenceError,
    ManuscriptNotFoundError,
    ManuscriptRepository,
    ManuscriptVersionConflictError,
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
from scholartrace.schemas import Claim, Manuscript, SectionContract

CREATED_AT = datetime(2026, 8, 11, tzinfo=UTC)


def create_projects(database_path: Path) -> None:
    repository = ProjectRepository(database_path)
    repository.create_project("lychee-m10", "thread-lychee-m10")
    repository.create_project("orchard-m10", "thread-orchard-m10")
    repository.close()


def manuscript(
    *,
    manuscript_id: str = "ms-m10-v1",
    version: int = 1,
    parent_manuscript_id: str | None = None,
    title: str = "Lychee pest detection study",
    project_id: str = "lychee-m10",
) -> Manuscript:
    return Manuscript(
        manuscript_id=manuscript_id,
        project_id=project_id,
        title=title,
        version=version,
        parent_manuscript_id=parent_manuscript_id,
        created_by="researcher-001",
        created_at=CREATED_AT,
    )


def setup_metric_provenance(database_path: Path) -> None:
    upgrade_database(database_path)
    create_projects(database_path)
    engine = create_sqlite_engine(database_path)
    with Session(engine) as session, session.begin():
        session.add(
            AlgorithmSpecRow(
                algorithm_id="algo-m10",
                project_id="lychee-m10",
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
                plan_id="plan-m10",
                project_id="lychee-m10",
                algorithm_id="algo-m10",
                version=1,
                content_sha256="b" * 64,
                payload={},
                status="frozen",
                created_by="researcher-001",
                created_at=CREATED_AT.replace(tzinfo=None),
            )
        )
        session.flush()
        session.add(
            RunManifestRow(
                run_id="run-m10",
                project_id="lychee-m10",
                plan_id="plan-m10",
                matrix_entry_id="matrix-m10",
                status="validated",
                payload={},
                created_at=CREATED_AT.replace(tzinfo=None),
            )
        )
        session.flush()
        session.add(
            MetricResultRow(
                metric_result_id="metric-m10",
                project_id="lychee-m10",
                run_id="run-m10",
                name="accuracy",
                split="validation",
                value=0.9,
                source="independent_recompute",
                verification_status="verified",
                is_final=True,
                payload={"data_version": "sha256:data-m10"},
                created_at=CREATED_AT.replace(tzinfo=None),
            )
        )
    engine.dispose()


def test_manuscript_migration_rolls_back_all_m10_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    assert current_revision(database_path) == LATEST_REVISION == "0018"
    tables = set(inspect(create_sqlite_engine(database_path)).get_table_names())
    assert {"manuscripts", "section_contracts", "claim_ledger"} <= tables
    downgrade_database(database_path, "0017")
    assert current_revision(database_path) == "0017"
    tables = set(inspect(create_sqlite_engine(database_path)).get_table_names())
    assert not {"manuscripts", "section_contracts", "claim_ledger"}.intersection(tables)
    upgrade_database(database_path)
    assert current_revision(database_path) == "0018"


def test_manuscript_versions_sections_and_project_isolation(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    create_projects(database_path)
    repository = ManuscriptRepository(database_path)
    first = repository.save_manuscript(manuscript())
    assert first.version == 1
    assert repository.save_manuscript(manuscript()) == first
    second = repository.save_manuscript(
        manuscript(
            manuscript_id="ms-m10-v2",
            version=2,
            parent_manuscript_id="ms-m10-v1",
            title="Lychee pest detection study, revised",
        )
    )
    assert [item.version for item in repository.list_manuscripts("lychee-m10")] == [1, 2]
    assert second.parent_manuscript_id == first.manuscript_id
    with pytest.raises(ManuscriptVersionConflictError, match="latest manuscript"):
        repository.save_manuscript(
            manuscript(
                manuscript_id="ms-m10-v3",
                version=3,
                parent_manuscript_id="wrong-parent",
                title="invalid lineage",
            )
        )
    contract = repository.save_section_contract(
        SectionContract(
            section_id="section-introduction",
            manuscript_id="ms-m10-v2",
            section="introduction",
            purpose="State the evidence-backed research gap.",
            required_evidence_ids=["evidence-001"],
            created_by="researcher-001",
            created_at=CREATED_AT,
        )
    )
    assert contract.content_sha256 is not None
    assert repository.list_section_contracts("ms-m10-v2")[0].section == "introduction"
    with pytest.raises(ManuscriptNotFoundError):
        repository.get_manuscript("orchard-m10", "ms-m10-v1")
    repository.close()


def test_claim_ledger_requires_evidence_for_supported_claims(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    setup_metric_provenance(database_path)
    repository = ManuscriptRepository(database_path)
    insufficient = repository.save_claim(
        Claim(
            claim_id="claim-m10-gap",
            project_id="lychee-m10",
            text="The evidence gap remains to be verified.",
            claim_type="limitation",
            status="insufficient",
            created_by="researcher-001",
            created_at=CREATED_AT,
        )
    )
    assert insufficient.status == "insufficient"
    supported = repository.save_claim(
        Claim(
            claim_id="claim-m10-result",
            project_id="lychee-m10",
            text="The proposed method reached the verified validation accuracy.",
            claim_type="result",
            status="supported",
            experiment_run_ids=["run-m10"],
            metric_result_ids=["metric-m10"],
            manuscript_locations=["results.accuracy"],
            created_by="researcher-001",
            created_at=CREATED_AT,
        )
    )
    assert supported.metric_result_ids == ["metric-m10"]
    assert repository.list_claims("lychee-m10")[1].claim_id == "claim-m10-result"
    with pytest.raises(ClaimEvidenceError, match="missing project metrics"):
        repository.save_claim(
            Claim(
                claim_id="claim-m10-missing",
                project_id="lychee-m10",
                text="This result has no traceable metric.",
                claim_type="result",
                status="supported",
                metric_result_ids=["metric-missing"],
                created_by="researcher-001",
                created_at=CREATED_AT,
            )
        )
    repository.close()


def test_claim_contract_rejects_unbound_supported_claim_and_conclusion_new_claims() -> None:
    with pytest.raises(ValueError, match="supported claims require"):
        Claim(
            text="Unsupported statement",
            claim_type="method",
            status="supported",
        )
    with pytest.raises(ValueError, match="conclusion contracts"):
        SectionContract(
            section="conclusion",
            purpose="Summarize supported findings.",
        )
