import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import inspect

from scholartrace.literature.chunking import chunk_document_text
from scholartrace.literature.evidence import (
    EvidenceCardService,
    EvidenceValidationError,
    citation_locator_for,
)
from scholartrace.literature.retrieval import HybridChunkIndex
from scholartrace.persistence.database import create_sqlite_engine
from scholartrace.persistence.literature_repository import (
    LiteratureRepository,
    ProjectDocumentConflictError,
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


def catalog_document(
    content_sha: str,
    title: str,
    *,
    abstract: str = "",
    doi: str | None = None,
    text_relpath: str | None = None,
) -> Document:
    return Document(
        document_id=document_id_for_content(content_sha),
        content_sha256=content_sha,
        mime_type="application/pdf",
        byte_size=100,
        source_type="uploaded_pdf",
        ingest_status="indexed",
        quality_status="ok",
        searchable=True,
        metadata=DocumentMetadata(
            title=title,
            abstract=abstract,
            authors=["Researcher"],
            doi=doi,
        ),
        text_relpath=text_relpath,
        created_at=datetime(2026, 8, 11, tzinfo=UTC),
    )


def create_project(database_path: Path, project_id: str) -> None:
    projects = ProjectRepository(database_path)
    projects.create_project(project_id, project_id)
    projects.close()


def test_evidence_card_migration_can_roll_back(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    assert current_revision(database_path) == LATEST_REVISION
    engine = create_sqlite_engine(database_path)
    assert "evidence_cards" in inspect(engine).get_table_names()
    engine.dispose()

    downgrade_database(database_path, "0006")
    assert current_revision(database_path) == "0006"
    engine = create_sqlite_engine(database_path)
    assert "evidence_cards" not in inspect(engine).get_table_names()
    engine.dispose()
    upgrade_database(database_path)
    assert current_revision(database_path) == LATEST_REVISION


def test_evidence_card_requires_approval_and_validates_runtime_quote(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    source_root = tmp_path / "library"
    source_root.mkdir()
    upgrade_database(database_path)
    create_project(database_path, "lychee-evidence")
    repository = LiteratureRepository(database_path)
    text = "Lychee disease appears on orchard leaves."
    document = repository.save_document(
        catalog_document(
            "a" * 64,
            "Lychee disease",
            doi="10.1234/synthetic.lychee",
            text_relpath="text/lychee.txt",
        )
    )
    repository.attach_document("lychee-evidence", document.document_id)
    chunks = chunk_document_text(document.document_id, text, max_chars=80)
    repository.replace_document_chunks(document.document_id, chunks)
    source_path = source_root / "text" / "lychee.txt"
    source_path.parent.mkdir()
    source_path.write_text(text, encoding="utf-8")
    repository.close()

    service = EvidenceCardService(database_path, source_root)
    with pytest.raises(ProjectDocumentConflictError, match="approved"):
        service.create_card(
            "lychee-evidence",
            chunks[0].chunk_id,
            statement="The source describes leaf symptoms.",
            quote="orchard leaves",
            verified_by="researcher-001",
        )

    repository = LiteratureRepository(database_path)
    repository.review_project_document(
        "lychee-evidence",
        document.document_id,
        status="approved",
        actor_id="researcher-001",
        reason="approved for evidence review",
    )
    repository.close()

    card = service.create_card(
        "lychee-evidence",
        chunks[0].chunk_id,
        statement="The source describes leaf symptoms.",
        quote="orchard leaves",
        verified_by="researcher-001",
    )
    assert card.locator_kind == "doi"
    assert card.locator_value == "10.1234/synthetic.lychee"
    assert (
        text[card.source_span.start_offset : card.source_span.end_offset] == card.source_span.quote
    )
    assert (
        service.create_card(
            "lychee-evidence",
            chunks[0].chunk_id,
            statement="The source describes leaf symptoms.",
            quote="orchard leaves",
            verified_by="researcher-001",
        )
        == card
    )
    assert service.list_project_cards("lychee-evidence") == [card]

    with pytest.raises(EvidenceValidationError, match="not present"):
        service.create_card(
            "lychee-evidence",
            chunks[0].chunk_id,
            statement="A different statement.",
            quote="invented result",
            verified_by="researcher-001",
        )
    source_path.write_text("tampered text", encoding="utf-8")
    with pytest.raises(EvidenceValidationError, match="runtime text"):
        service.create_card(
            "lychee-evidence",
            chunks[0].chunk_id,
            statement="The source still describes disease.",
            quote="Lychee disease",
            verified_by="researcher-001",
        )
    service.close()


def test_missing_citation_locator_is_rejected_after_approval(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    create_project(database_path, "no-locator")
    repository = LiteratureRepository(database_path)
    document = repository.save_document(catalog_document("b" * 64, "No locator"))
    repository.attach_document("no-locator", document.document_id)
    chunks = chunk_document_text(document.document_id, "A verified source span.", max_chars=80)
    repository.replace_document_chunks(document.document_id, chunks)
    repository.review_project_document(
        "no-locator",
        document.document_id,
        status="approved",
        actor_id="researcher-001",
        reason="manual approval",
    )
    repository.close()

    service = EvidenceCardService(database_path)
    with pytest.raises(EvidenceValidationError, match="no valid DOI"):
        service.create_card(
            "no-locator",
            chunks[0].chunk_id,
            statement="The source contains a span.",
            quote="verified source span",
            verified_by="researcher-001",
        )
    service.close()


def test_citation_locator_requires_a_parseable_external_or_safe_local_source() -> None:
    url_document = catalog_document("f" * 64, "URL source").model_copy(
        update={"metadata": DocumentMetadata(url="https://example.invalid/paper")}
    )
    assert citation_locator_for(url_document) == ("url", "https://example.invalid/paper")

    local_document = catalog_document("0" * 64, "Local source").model_copy(
        update={"text_relpath": "text/source.txt"}
    )
    assert citation_locator_for(local_document) == ("local", "text/source.txt")

    unsafe_document = catalog_document("1" * 64, "Unsafe source").model_copy(
        update={"text_relpath": "../private.txt"}
    )
    with pytest.raises(EvidenceValidationError, match="no valid DOI"):
        citation_locator_for(unsafe_document)


def test_fixed_retrieval_regression_set_has_expected_top_one(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    create_project(database_path, "regression-m4")
    repository = LiteratureRepository(database_path)
    corpus = {
        "lychee": (
            "c" * 64,
            "Lychee disease and orchard fruit images",
            (
                "Lychee disease leaves orchard fruit images leaf symptoms disease "
                "fruit orchard monitoring"
            ),
        ),
        "wheat": (
            "d" * 64,
            "Wheat yield forecasting",
            "Wheat yield forecasting satellite regression crop forecasting satellite",
        ),
        "orchard": (
            "e" * 64,
            "Orchard fruit counting",
            "Orchard fruit counting camera canopy object detection fruit counting",
        ),
    }
    document_ids: dict[str, str] = {}
    for label, (content_sha, title, text) in corpus.items():
        document = repository.save_document(
            catalog_document(content_sha, title, abstract=text, text_relpath=f"text/{label}.txt")
        )
        document_ids[label] = document.document_id
        repository.attach_document("regression-m4", document.document_id)
        repository.replace_document_chunks(
            document.document_id,
            chunk_document_text(document.document_id, text, max_chars=500),
        )
        repository.review_project_document(
            "regression-m4",
            document.document_id,
            status="approved",
            actor_id="regression-fixture",
            reason="fixed offline regression fixture",
        )

    index = HybridChunkIndex(tmp_path / "indexes")
    index.rebuild_project("regression-m4", repository)
    cases = json.loads(
        (Path(__file__).parents[1] / "fixtures" / "retrieval" / "m4-regression.json").read_text(
            encoding="utf-8"
        )
    )
    assert len(cases) == 10
    for case in cases:
        results = index.search("regression-m4", case["query"], top_k=3)
        assert results, case["case_id"]
        assert results[0].chunk.document_id == document_ids[case["expected_document"]]
    repository.close()
