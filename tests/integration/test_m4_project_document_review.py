from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import inspect

from scholartrace.persistence.database import create_sqlite_engine
from scholartrace.persistence.literature_repository import (
    LiteratureRepository,
    document_id_for_content,
)
from scholartrace.persistence.migrations import (
    LATEST_REVISION,
    current_revision,
    downgrade_database,
    upgrade_database,
)
from scholartrace.persistence.repository import ProjectRepository
from scholartrace.schemas import Document, DocumentMetadata


def catalog_document(content_sha: str, title: str, *, searchable: bool = True) -> Document:
    return Document(
        document_id=document_id_for_content(content_sha),
        content_sha256=content_sha,
        mime_type="application/pdf",
        byte_size=100,
        source_type="uploaded_pdf",
        ingest_status="indexed" if searchable else "failed",
        quality_status="ok" if searchable else "parse_failed",
        searchable=searchable,
        metadata=DocumentMetadata(title=title, authors=["Researcher"], year=2024),
        created_at=datetime(2026, 8, 11, tzinfo=UTC),
    )


def test_project_document_review_migration_can_roll_back(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    assert current_revision(database_path) == LATEST_REVISION
    engine = create_sqlite_engine(database_path)
    columns = {item["name"] for item in inspect(engine).get_columns("project_documents")}
    assert {"relevance_score", "relevance_reason", "decided_by", "decided_at"} <= columns
    engine.dispose()

    downgrade_database(database_path, "0004")
    assert current_revision(database_path) == "0004"
    engine = create_sqlite_engine(database_path)
    columns = {item["name"] for item in inspect(engine).get_columns("project_documents")}
    assert not {"relevance_score", "relevance_reason", "decided_by", "decided_at"} & columns
    engine.dispose()

    upgrade_database(database_path)
    assert current_revision(database_path) == LATEST_REVISION


def test_candidate_relevance_and_review_are_project_scoped(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    projects = ProjectRepository(database_path)
    projects.create_project("lychee-m4", "lychee-m4")
    projects.close()

    repository = LiteratureRepository(database_path)
    relevant = repository.save_document(
        catalog_document("a" * 64, "Lychee disease detection in orchard images")
    )
    unrelated = repository.save_document(catalog_document("b" * 64, "Wheat yield forecasting"))
    repository.attach_document("lychee-m4", relevant.document_id)
    repository.attach_document("lychee-m4", unrelated.document_id)

    ranked = repository.rank_project_candidates("lychee-m4", "lychee disease")
    assert ranked[0].document.document_id == relevant.document_id
    assert ranked[0].score > ranked[1].score
    assert ranked[0].matched_terms == ("disease", "lychee")

    approved = repository.review_project_document(
        "lychee-m4",
        relevant.document_id,
        status="approved",
        actor_id="researcher-001",
        reason="标题和研究域与黄金问题一致",
        relevance_score=ranked[0].score,
    )
    rejected = repository.review_project_document(
        "lychee-m4",
        unrelated.document_id,
        status="rejected",
        actor_id="researcher-001",
        reason="研究对象不匹配",
        relevance_score=ranked[1].score,
    )
    assert approved.status == "approved"
    assert approved.decided_by == "researcher-001"
    assert approved.relevance_score == ranked[0].score
    assert rejected.status == "rejected"
    assert [doc.document_id for doc in repository.list_approved_documents("lychee-m4")] == [
        relevant.document_id
    ]
    assert repository.get_document(relevant.document_id).document_id == relevant.document_id
    repository.close()


def test_failed_document_cannot_be_approved_and_reason_is_required(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    projects = ProjectRepository(database_path)
    projects.create_project("lychee-m4-failed", "lychee-m4-failed")
    projects.close()
    repository = LiteratureRepository(database_path)
    failed = repository.save_document(catalog_document("c" * 64, "Broken PDF", searchable=False))
    repository.attach_document("lychee-m4-failed", failed.document_id)
    with pytest.raises(ValueError, match="reason"):
        repository.review_project_document(
            "lychee-m4-failed",
            failed.document_id,
            status="approved",
            actor_id="researcher-001",
            reason="   ",
        )
    with pytest.raises(RuntimeError, match="cannot be approved"):
        repository.review_project_document(
            "lychee-m4-failed",
            failed.document_id,
            status="approved",
            actor_id="researcher-001",
            reason="人工审核但文件解析失败",
        )
    repository.close()
