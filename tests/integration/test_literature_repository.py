from datetime import UTC, datetime
from pathlib import Path

import pytest

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


def document(content_sha256: str, *, title: str = "Lychee disease detection") -> Document:
    return Document(
        document_id=document_id_for_content(content_sha256),
        content_sha256=content_sha256,
        mime_type="application/pdf",
        byte_size=128,
        source_type="uploaded_pdf",
        ingest_status="indexed",
        quality_status="metadata_incomplete",
        searchable=True,
        metadata=DocumentMetadata(title=title, authors=["Researcher One"], year=2024),
        storage_relpath="documents/example.pdf",
        text_relpath="text/example.txt",
        parser_version="test-parser",
        created_at=datetime(2026, 8, 11, tzinfo=UTC),
    )


def test_literature_migration_rolls_back_without_leaving_catalog_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    assert current_revision(database_path) == LATEST_REVISION

    from sqlalchemy import inspect

    from scholartrace.persistence.database import create_sqlite_engine

    engine = create_sqlite_engine(database_path)
    assert {"documents", "project_documents"} <= set(inspect(engine).get_table_names())
    engine.dispose()

    downgrade_database(database_path, "0003")
    engine = create_sqlite_engine(database_path)
    assert current_revision(database_path) == "0003"
    assert "documents" not in inspect(engine).get_table_names()
    assert "project_documents" not in inspect(engine).get_table_names()
    engine.dispose()

    upgrade_database(database_path)
    assert current_revision(database_path) == LATEST_REVISION


def test_document_hash_deduplication_catalog_search_and_project_link(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    project_repository = ProjectRepository(database_path)
    project_repository.create_project("lychee-literature", "lychee-literature")
    project_repository.close()

    repository = LiteratureRepository(database_path)
    content_sha256 = "a" * 64
    first = repository.save_document(document(content_sha256))
    replay = repository.save_document(document(content_sha256))
    assert replay == first
    assert [item.document_id for item in repository.search_catalog("lychee")] == [first.document_id]

    linked = repository.attach_document("lychee-literature", first.document_id)
    assert repository.attach_document("lychee-literature", first.document_id) == linked
    assert repository.list_project_documents("lychee-literature") == [linked]

    failed = document("b" * 64, title="Broken upload").model_copy(
        update={"ingest_status": "failed", "quality_status": "parse_failed", "searchable": False}
    )
    repository.save_document(failed)
    assert repository.search_catalog("broken") == []
    assert [item.document_id for item in repository.list_documents(include_failed=True)] == [
        first.document_id,
        failed.document_id,
    ]
    repository.close()


def test_document_schema_rejects_unknown_source_or_hash(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        document("not-a-sha256")

    payload = document("c" * 64).model_dump()
    payload["source_type"] = "invented"
    with pytest.raises(ValueError):
        Document.model_validate(payload)
