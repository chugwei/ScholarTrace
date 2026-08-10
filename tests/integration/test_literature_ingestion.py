import os
import stat
from pathlib import Path

from pypdf import PdfWriter

from scholartrace.literature.ingestion import DocumentLibrary
from scholartrace.persistence.repository import ProjectRepository
from scholartrace.schemas import DocumentMetadata


def write_pdf(path: Path, *, title: str = "Lychee disease evidence") -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_metadata(
        {"/Title": title, "/Author": "Researcher One", "/CreationDate": "D:20240101"}
    )
    with path.open("wb") as handle:
        writer.write(handle)


def test_pdf_ingestion_deduplicates_and_stores_read_only_runtime_files(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    duplicate = tmp_path / "duplicate.pdf"
    write_pdf(source)
    duplicate.write_bytes(source.read_bytes())

    library = DocumentLibrary(tmp_path / "domain.db", tmp_path / "library")
    first = library.ingest_pdf(source)
    replay = library.ingest_pdf(duplicate)

    assert replay == first
    assert first.ingest_status == "indexed"
    assert first.quality_status == "empty_text"
    assert first.metadata.title == "Lychee disease evidence"
    assert first.metadata.authors == ["Researcher One"]
    assert first.metadata.year == 2024
    pdf_path = tmp_path / "library" / first.storage_relpath
    text_path = tmp_path / "library" / first.text_relpath
    assert pdf_path.exists()
    assert text_path.exists()
    assert not os.stat(pdf_path).st_mode & stat.S_IWRITE
    assert library.repository.search_catalog("lychee") == [first]
    library.close()


def test_invalid_pdf_is_recorded_as_failed_but_not_searchable(tmp_path: Path) -> None:
    invalid = tmp_path / "broken.pdf"
    invalid.write_bytes(b"not a PDF and not a research source")

    library = DocumentLibrary(tmp_path / "domain.db", tmp_path / "library")
    failed = library.ingest_pdf(
        invalid,
        metadata=DocumentMetadata(title="Broken upload", authors=["Unknown source"]),
    )

    assert failed.ingest_status == "failed"
    assert failed.quality_status == "parse_failed"
    assert failed.searchable is False
    assert failed.storage_relpath is None
    assert library.repository.search_catalog("broken") == []
    assert library.repository.list_documents() == []
    assert library.repository.list_documents(include_failed=True) == [failed]
    library.close()


def test_pdf_can_be_attached_as_a_candidate_without_becoming_evidence(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    write_pdf(source, title="Agriculture vision candidate")
    project_repository = ProjectRepository(tmp_path / "domain.db")
    from scholartrace.persistence.migrations import upgrade_database

    project_repository.close()
    upgrade_database(tmp_path / "domain.db")
    project_repository = ProjectRepository(tmp_path / "domain.db")
    project_repository.create_project("orchard-literature", "orchard-literature")
    project_repository.close()

    library = DocumentLibrary(tmp_path / "domain.db", tmp_path / "library")
    ingested = library.ingest_pdf(source)
    link = library.repository.attach_document("orchard-literature", ingested.document_id)
    assert link.status == "candidate"
    library.close()
