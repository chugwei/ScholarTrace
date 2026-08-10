"""Deterministic, local-first PDF ingestion for the literature catalog."""

from __future__ import annotations

import hashlib
import re
import stat
from io import BytesIO
from pathlib import Path
from typing import Any

import pypdf
from pypdf import PdfReader

from scholartrace.literature.chunking import chunk_document_text
from scholartrace.persistence.literature_repository import (
    LiteratureRepository,
    document_id_for_content,
)
from scholartrace.persistence.migrations import upgrade_database
from scholartrace.persistence.models import utc_now_naive
from scholartrace.schemas import Document, DocumentChunk, DocumentMetadata

_DOI_PATTERN = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
_YEAR_PATTERN = re.compile(r"(?:19|20)\d{2}")


class DocumentIngestError(RuntimeError):
    """Raised when the input file cannot be read before a catalog row exists."""


class DocumentLibrary:
    """Store approved local inputs outside Git and catalog only verified parses."""

    def __init__(self, database_path: Path, storage_root: Path) -> None:
        upgrade_database(database_path)
        self.repository = LiteratureRepository(database_path)
        self.storage_root = storage_root.expanduser().resolve()
        self.storage_root.mkdir(parents=True, exist_ok=True)

    def close(self) -> None:
        self.repository.close()

    def index_document_text(
        self,
        document_id: str,
        *,
        max_chars: int = 800,
        overlap_chars: int | None = None,
    ) -> list[DocumentChunk]:
        """Read a cataloged text artifact and persist traceable chunks."""

        document = self.repository.get_document(document_id)
        if not document.text_relpath:
            raise DocumentIngestError("document has no stored searchable text")
        text_path = (self.storage_root / document.text_relpath).resolve()
        if not text_path.is_relative_to(self.storage_root):
            raise DocumentIngestError("document text path escapes the storage root")
        try:
            text = text_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise DocumentIngestError("could not read stored document text") from error
        chunks = chunk_document_text(
            document.document_id,
            text,
            max_chars=max_chars,
            overlap_chars=overlap_chars,
        )
        return self.repository.replace_document_chunks(document.document_id, chunks)

    def ingest_pdf(
        self,
        source_path: Path,
        *,
        metadata: DocumentMetadata | None = None,
        source_type: str = "uploaded_pdf",
    ) -> Document:
        """Ingest a local PDF; parse failures are cataloged but never searchable."""

        resolved_source = source_path.expanduser().resolve()
        try:
            content = resolved_source.read_bytes()
        except (OSError, UnicodeError) as error:
            raise DocumentIngestError(f"could not read PDF {resolved_source.name!r}") from error

        content_sha256 = hashlib.sha256(content).hexdigest()
        existing = self.repository.find_by_content_sha256(content_sha256)
        if existing is not None:
            return existing
        document_id = document_id_for_content(content_sha256)
        base_metadata = metadata or DocumentMetadata()
        parser_version = f"pypdf-{pypdf.__version__}"

        if not content.startswith(b"%PDF-"):
            failed = _document(
                document_id=document_id,
                content_sha256=content_sha256,
                byte_size=len(content),
                source_type=source_type,
                ingest_status="failed",
                quality_status="parse_failed",
                searchable=False,
                metadata=base_metadata,
                parser_version=parser_version,
            )
            return self.repository.save_document(failed)

        try:
            reader = PdfReader(stream=BytesIO(content))
            parsed_metadata, text = _parse_pdf(reader, base_metadata)
        except Exception:
            failed = _document(
                document_id=document_id,
                content_sha256=content_sha256,
                byte_size=len(content),
                source_type=source_type,
                ingest_status="failed",
                quality_status="parse_failed",
                searchable=False,
                metadata=base_metadata,
                parser_version=parser_version,
            )
            return self.repository.save_document(failed)

        quality_status = "empty_text" if not text.strip() else "ok"
        if quality_status == "ok" and not any(
            [parsed_metadata.title, parsed_metadata.doi, parsed_metadata.url]
        ):
            quality_status = "metadata_incomplete"
        pdf_relpath = Path("documents") / f"{document_id}.pdf"
        text_relpath = Path("text") / f"{document_id}.txt"
        _write_readonly(self.storage_root / pdf_relpath, content)
        _write_readonly(self.storage_root / text_relpath, text.encode("utf-8"))
        indexed = _document(
            document_id=document_id,
            content_sha256=content_sha256,
            byte_size=len(content),
            source_type=source_type,
            ingest_status="indexed",
            quality_status=quality_status,
            searchable=True,
            metadata=parsed_metadata,
            storage_relpath=pdf_relpath,
            text_relpath=text_relpath,
            parser_version=parser_version,
        )
        return self.repository.save_document(indexed)


def _parse_pdf(reader: PdfReader, provided: DocumentMetadata) -> tuple[DocumentMetadata, str]:
    pdf_metadata = reader.metadata or {}
    title = provided.title or _string_metadata(pdf_metadata, "/Title")
    authors = provided.authors or _authors_from_metadata(_string_metadata(pdf_metadata, "/Author"))
    year = provided.year or _year_from_metadata(_string_metadata(pdf_metadata, "/CreationDate"))
    text_parts: list[str] = []
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")
    text = "\n".join(part for part in text_parts if part)
    doi = provided.doi or _first_doi(text)
    url = provided.url
    abstract = provided.abstract
    return (
        DocumentMetadata(
            title=title,
            authors=authors,
            abstract=abstract,
            year=year,
            doi=doi,
            url=url,
        ),
        text,
    )


def _string_metadata(metadata: Any, key: str) -> str | None:
    value = metadata.get(key) if hasattr(metadata, "get") else None
    return str(value).strip() if value is not None and str(value).strip() else None


def _authors_from_metadata(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in re.split(r";|,", value) if item.strip()]


def _year_from_metadata(value: str | None) -> int | None:
    if not value:
        return None
    match = _YEAR_PATTERN.search(value)
    return int(match.group()) if match else None


def _first_doi(text: str) -> str | None:
    match = _DOI_PATTERN.search(text)
    if match is None:
        return None
    return match.group().rstrip(".,;)")


def _write_readonly(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)
    path.chmod(stat.S_IREAD)


def _document(
    *,
    document_id: str,
    content_sha256: str,
    byte_size: int,
    source_type: str,
    ingest_status: str,
    quality_status: str,
    searchable: bool,
    metadata: DocumentMetadata,
    parser_version: str,
    storage_relpath: Path | None = None,
    text_relpath: Path | None = None,
) -> Document:
    return Document.model_validate(
        {
            "document_id": document_id,
            "content_sha256": content_sha256,
            "mime_type": "application/pdf",
            "byte_size": byte_size,
            "source_type": source_type,
            "ingest_status": ingest_status,
            "quality_status": quality_status,
            "searchable": searchable,
            "metadata": metadata,
            "storage_relpath": storage_relpath.as_posix() if storage_relpath else None,
            "text_relpath": text_relpath.as_posix() if text_relpath else None,
            "parser_version": parser_version,
            "created_at": utc_now_naive(),
        }
    )
