from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import inspect

from scholartrace.literature.chunking import chunk_document_text
from scholartrace.literature.ingestion import DocumentLibrary
from scholartrace.literature.retrieval import HashingEmbeddingProvider, HybridChunkIndex
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


def catalog_document(content_sha: str, title: str, abstract: str = "") -> Document:
    return Document(
        document_id=document_id_for_content(content_sha),
        content_sha256=content_sha,
        mime_type="application/pdf",
        byte_size=100,
        source_type="uploaded_pdf",
        ingest_status="indexed",
        quality_status="ok",
        searchable=True,
        metadata=DocumentMetadata(title=title, abstract=abstract, authors=["Researcher"]),
        created_at=datetime(2026, 8, 11, tzinfo=UTC),
    )


def create_project(database_path: Path, project_id: str) -> None:
    projects = ProjectRepository(database_path)
    projects.create_project(project_id, project_id)
    projects.close()


def test_document_chunk_migration_and_offsets_round_trip(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    assert current_revision(database_path) == LATEST_REVISION
    engine = create_sqlite_engine(database_path)
    assert "document_chunks" in inspect(engine).get_table_names()
    engine.dispose()

    repository = LiteratureRepository(database_path)
    document = repository.save_document(catalog_document("a" * 64, "Lychee disease"))
    text = "Lychee disease appears in orchard images. Collect leaf and fruit examples."
    chunks = chunk_document_text(
        document.document_id,
        text,
        max_chars=32,
        overlap_chars=8,
        created_at=datetime(2026, 8, 11),
    )
    assert chunks
    assert all(text[chunk.start_offset : chunk.end_offset] == chunk.text for chunk in chunks)
    assert [chunk.ordinal for chunk in chunks] == list(range(len(chunks)))
    assert repository.replace_document_chunks(document.document_id, chunks) == chunks
    assert repository.list_document_chunks(document.document_id) == chunks
    repository.close()

    downgrade_database(database_path, "0005")
    engine = create_sqlite_engine(database_path)
    assert current_revision(database_path) == "0005"
    assert "document_chunks" not in inspect(engine).get_table_names()
    engine.dispose()
    upgrade_database(database_path)
    assert current_revision(database_path) == LATEST_REVISION


def test_project_index_uses_approved_chunks_and_preserves_source_span(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    create_project(database_path, "lychee-m4")
    repository = LiteratureRepository(database_path)
    relevant = repository.save_document(
        catalog_document(
            "a" * 64,
            "Lychee disease detection",
            "Orchard leaf symptoms and fruit images.",
        )
    )
    unrelated = repository.save_document(
        catalog_document("b" * 64, "Wheat yield forecasting", "Satellite regression.")
    )
    repository.attach_document("lychee-m4", relevant.document_id)
    repository.attach_document("lychee-m4", unrelated.document_id)
    relevant_chunks = chunk_document_text(
        relevant.document_id,
        "Lychee disease appears on orchard leaves.",
        max_chars=80,
    )
    unrelated_chunks = chunk_document_text(
        unrelated.document_id,
        "Wheat yield forecasting uses satellite regression.",
        max_chars=80,
    )
    repository.replace_document_chunks(relevant.document_id, relevant_chunks)
    repository.replace_document_chunks(unrelated.document_id, unrelated_chunks)
    repository.review_project_document(
        "lychee-m4",
        relevant.document_id,
        status="approved",
        actor_id="researcher-001",
        reason="研究对象和数据模态匹配",
    )

    index = HybridChunkIndex(tmp_path / "indexes")
    snapshot = index.rebuild_project("lychee-m4", repository)
    assert {chunk.document_id for chunk in snapshot.chunks} == {relevant.document_id}
    results = index.search("lychee-m4", "lychee disease", top_k=3)
    assert results
    result = results[0]
    assert result.chunk.document_id == relevant.document_id
    assert result.lexical_score > 0
    assert result.vector_score > 0
    assert result.index_generation == snapshot.generation
    assert result.chunk.text == "Lychee disease appears on orchard leaves."
    repository.close()


def test_failed_rebuild_keeps_the_previous_index_available(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    create_project(database_path, "lychee-m4-rebuild")
    repository = LiteratureRepository(database_path)
    document = repository.save_document(catalog_document("c" * 64, "Lychee disease"))
    repository.attach_document("lychee-m4-rebuild", document.document_id)
    repository.replace_document_chunks(
        document.document_id,
        chunk_document_text(document.document_id, "Lychee disease orchard images", max_chars=80),
    )
    repository.review_project_document(
        "lychee-m4-rebuild",
        document.document_id,
        status="approved",
        actor_id="researcher-001",
        reason="黄金问题匹配",
    )

    index_root = tmp_path / "indexes"
    healthy = HybridChunkIndex(index_root, HashingEmbeddingProvider())
    old_snapshot = healthy.rebuild_project("lychee-m4-rebuild", repository)
    index_path = index_root / "lychee-m4-rebuild.hybrid.json"
    old_payload = index_path.read_bytes()

    class FailingProvider:
        name = "hashing-v1"
        dimensions = 64

        def embed(self, text: str) -> list[float]:
            raise RuntimeError("vector service unavailable")

    failing = HybridChunkIndex(index_root, FailingProvider())
    with pytest.raises(RuntimeError, match="vector service unavailable"):
        failing.rebuild_project("lychee-m4-rebuild", repository)
    assert index_path.read_bytes() == old_payload

    restored = HybridChunkIndex(index_root, HashingEmbeddingProvider())
    assert restored.load("lychee-m4-rebuild").generation == old_snapshot.generation
    assert restored.search("lychee-m4-rebuild", "lychee disease")
    repository.close()


def test_document_library_indexes_the_stored_text_artifact(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    storage_root = tmp_path / "library"
    library = DocumentLibrary(database_path, storage_root)
    document = library.repository.save_document(
        catalog_document("d" * 64, "Lychee disease").model_copy(
            update={"text_relpath": "text/lychee.txt"}
        )
    )
    text = "Lychee disease evidence from orchard leaves."
    text_path = storage_root / "text" / "lychee.txt"
    text_path.parent.mkdir(parents=True)
    text_path.write_text(text, encoding="utf-8")
    chunks = library.index_document_text(document.document_id, max_chars=20)
    assert chunks
    assert all(text[chunk.start_offset : chunk.end_offset] == chunk.text for chunk in chunks)
    assert library.repository.list_document_chunks(document.document_id) == chunks
    library.close()
