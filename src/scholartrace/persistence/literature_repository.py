"""Transactional persistence for the independent literature catalog."""

import hashlib
from pathlib import Path

from sqlalchemy import String, cast, delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from scholartrace.identifiers import validate_identifier
from scholartrace.literature_relevance import RelevanceScore, score_document_relevance
from scholartrace.persistence.database import create_sqlite_engine
from scholartrace.persistence.models import (
    DocumentChunkRow,
    DocumentRow,
    ProjectDocumentRow,
    ProjectRow,
    utc_now_naive,
)
from scholartrace.schemas import Document, DocumentChunk, ProjectDocument


class LiteratureRepositoryError(RuntimeError):
    """Base error for literature catalog operations."""


class DocumentNotFoundError(LiteratureRepositoryError):
    """Raised when a document-scoped operation cannot find its document."""


class DocumentConflictError(LiteratureRepositoryError):
    """Raised when a stable document ID or content hash is reused incorrectly."""


class ProjectDocumentConflictError(LiteratureRepositoryError):
    """Raised when a project/document association is reused with different identity."""


class LiteratureRepository:
    """Persist global documents and project links in the existing domain database."""

    def __init__(self, database_path: Path) -> None:
        self._engine = create_sqlite_engine(database_path)

    def close(self) -> None:
        self._engine.dispose()

    def save_document(self, document: Document) -> Document:
        """Insert a document once, returning the existing row on content replay."""

        with Session(self._engine) as session, session.begin():
            existing = session.scalar(
                select(DocumentRow).where(DocumentRow.content_sha256 == document.content_sha256)
            )
            if existing is not None:
                if existing.document_id != document.document_id:
                    raise DocumentConflictError(
                        "content_sha256 is already bound to a different document_id"
                    )
                return _document_model(existing)

            conflicting_id = session.get(DocumentRow, document.document_id)
            if conflicting_id is not None:
                raise DocumentConflictError(
                    f"document_id {document.document_id!r} already has different content"
                )
            row = DocumentRow(
                document_id=document.document_id,
                content_sha256=document.content_sha256,
                mime_type=document.mime_type,
                byte_size=document.byte_size,
                source_type=document.source_type,
                ingest_status=document.ingest_status,
                quality_status=document.quality_status,
                searchable=document.searchable,
                title=document.metadata.title,
                authors=document.metadata.authors,
                abstract=document.metadata.abstract,
                year=document.metadata.year,
                doi=document.metadata.doi,
                url=document.metadata.url,
                storage_relpath=document.storage_relpath,
                text_relpath=document.text_relpath,
                parser_version=document.parser_version,
                created_at=document.created_at.replace(tzinfo=None),
            )
            session.add(row)
            try:
                session.flush()
            except IntegrityError as error:
                raise DocumentConflictError("document identity is already persisted") from error
            return _document_model(row)

    def get_document(self, document_id: str) -> Document:
        document_id = validate_identifier(document_id)
        with Session(self._engine) as session:
            row = session.get(DocumentRow, document_id)
            if row is None:
                raise DocumentNotFoundError(f"document {document_id!r} was not found")
            return _document_model(row)

    def find_by_content_sha256(self, content_sha256: str) -> Document | None:
        if len(content_sha256) != 64:
            raise ValueError("content_sha256 must contain 64 hexadecimal characters")
        with Session(self._engine) as session:
            row = session.scalar(
                select(DocumentRow).where(DocumentRow.content_sha256 == content_sha256)
            )
            return _document_model(row) if row is not None else None

    def list_documents(self, *, include_failed: bool = False) -> list[Document]:
        with Session(self._engine) as session:
            statement = select(DocumentRow)
            if not include_failed:
                statement = statement.where(DocumentRow.ingest_status != "failed")
            rows = session.scalars(
                statement.order_by(DocumentRow.created_at, DocumentRow.document_id)
            ).all()
            return [_document_model(row) for row in rows]

    def search_catalog(self, query: str = "") -> list[Document]:
        """Search metadata only; failed or non-searchable files never enter results."""

        normalized = query.strip().lower()
        with Session(self._engine) as session:
            statement = select(DocumentRow).where(
                DocumentRow.searchable.is_(True),
                DocumentRow.ingest_status != "failed",
            )
            if normalized:
                pattern = f"%{normalized}%"
                searchable_fields = [
                    DocumentRow.title,
                    cast(DocumentRow.authors, String),
                    DocumentRow.abstract,
                    DocumentRow.doi,
                    DocumentRow.url,
                ]
                statement = statement.where(
                    or_(
                        *[
                            func.lower(func.coalesce(field, "")).like(pattern)
                            for field in searchable_fields
                        ]
                    )
                )
            rows = session.scalars(
                statement.order_by(DocumentRow.title, DocumentRow.document_id)
            ).all()
            return [_document_model(row) for row in rows]

    def attach_document(
        self,
        project_id: str,
        document_id: str,
        status: str = "candidate",
    ) -> ProjectDocument:
        project_id = validate_identifier(project_id)
        document_id = validate_identifier(document_id)
        if status != "candidate":
            raise ValueError("M3 project document status must be candidate")
        with Session(self._engine) as session, session.begin():
            if session.get(ProjectRow, project_id) is None:
                raise LiteratureRepositoryError(f"project {project_id!r} was not found")
            if session.get(DocumentRow, document_id) is None:
                raise DocumentNotFoundError(f"document {document_id!r} was not found")
            project_document_id = project_document_id_for(project_id, document_id)
            existing = session.get(ProjectDocumentRow, project_document_id)
            if existing is not None:
                if existing.project_id != project_id or existing.document_id != document_id:
                    raise ProjectDocumentConflictError(
                        f"project_document_id {project_document_id!r} has different identity"
                    )
                return _project_document_model(existing)
            row = ProjectDocumentRow(
                project_document_id=project_document_id,
                project_id=project_id,
                document_id=document_id,
                status=status,
                created_at=utc_now_naive(),
            )
            session.add(row)
            session.flush()
            return _project_document_model(row)

    def review_project_document(
        self,
        project_id: str,
        document_id: str,
        *,
        status: str,
        actor_id: str,
        reason: str,
        relevance_score: float | None = None,
    ) -> ProjectDocument:
        """Record a project-scoped approval decision without changing the global document."""

        project_id = validate_identifier(project_id)
        document_id = validate_identifier(document_id)
        actor_id = validate_identifier(actor_id)
        if status not in {"approved", "rejected"}:
            raise ValueError("review status must be approved or rejected")
        if not reason.strip():
            raise ValueError("review reason is required")
        if relevance_score is not None and not 0 <= relevance_score <= 1:
            raise ValueError("relevance_score must be between 0 and 1")
        with Session(self._engine) as session, session.begin():
            row = session.scalar(
                select(ProjectDocumentRow).where(
                    ProjectDocumentRow.project_id == project_id,
                    ProjectDocumentRow.document_id == document_id,
                )
            )
            if row is None:
                raise ProjectDocumentConflictError(
                    "document must be attached as candidate before review"
                )
            document = session.get(DocumentRow, document_id)
            if document is None:
                raise DocumentNotFoundError(f"document {document_id!r} was not found")
            if status == "approved" and (
                document.ingest_status == "failed" or not document.searchable
            ):
                raise LiteratureRepositoryError(
                    "failed or non-searchable documents cannot be approved"
                )
            row.status = status
            row.relevance_score = relevance_score
            row.relevance_reason = reason.strip()
            row.decided_by = actor_id
            row.decided_at = utc_now_naive()
            session.flush()
            return _project_document_model(row)

    def rank_project_candidates(self, project_id: str, query: str) -> list[RelevanceScore]:
        """Rank only candidate links using deterministic metadata overlap."""

        project_id = validate_identifier(project_id)
        with Session(self._engine) as session:
            rows = session.scalars(
                select(ProjectDocumentRow)
                .where(
                    ProjectDocumentRow.project_id == project_id,
                    ProjectDocumentRow.status == "candidate",
                )
                .order_by(ProjectDocumentRow.document_id)
            ).all()
            scores: list[RelevanceScore] = []
            for link in rows:
                document = session.get(DocumentRow, link.document_id)
                if document is None:
                    continue
                scores.append(score_document_relevance(query, _document_model(document)))
            return sorted(scores, key=lambda item: (-item.score, item.document.document_id))

    def list_approved_documents(self, project_id: str) -> list[Document]:
        """Return only project documents explicitly approved by a human."""

        project_id = validate_identifier(project_id)
        with Session(self._engine) as session:
            rows = session.scalars(
                select(DocumentRow)
                .join(
                    ProjectDocumentRow,
                    ProjectDocumentRow.document_id == DocumentRow.document_id,
                )
                .where(
                    ProjectDocumentRow.project_id == project_id,
                    ProjectDocumentRow.status == "approved",
                )
                .order_by(DocumentRow.document_id)
            ).all()
            return [_document_model(row) for row in rows]

    def replace_document_chunks(
        self, document_id: str, chunks: list[DocumentChunk]
    ) -> list[DocumentChunk]:
        """Replace a document's chunks atomically after validating their identity."""

        document_id = validate_identifier(document_id)
        if any(chunk.document_id != document_id for chunk in chunks):
            raise ValueError("all chunks must belong to document_id")
        ordinals = [chunk.ordinal for chunk in chunks]
        if len(ordinals) != len(set(ordinals)):
            raise ValueError("chunk ordinals must be unique per document")
        with Session(self._engine) as session, session.begin():
            if session.get(DocumentRow, document_id) is None:
                raise DocumentNotFoundError(f"document {document_id!r} was not found")
            session.execute(
                delete(DocumentChunkRow).where(DocumentChunkRow.document_id == document_id)
            )
            session.add_all(
                DocumentChunkRow(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    ordinal=chunk.ordinal,
                    text=chunk.text,
                    start_offset=chunk.start_offset,
                    end_offset=chunk.end_offset,
                    content_sha256=chunk.content_sha256,
                    created_at=chunk.created_at.replace(tzinfo=None),
                )
                for chunk in chunks
            )
            session.flush()
            return [_chunk_model(row) for row in sorted(chunks, key=lambda item: item.ordinal)]

    def list_document_chunks(self, document_id: str) -> list[DocumentChunk]:
        document_id = validate_identifier(document_id)
        with Session(self._engine) as session:
            if session.get(DocumentRow, document_id) is None:
                raise DocumentNotFoundError(f"document {document_id!r} was not found")
            rows = session.scalars(
                select(DocumentChunkRow)
                .where(DocumentChunkRow.document_id == document_id)
                .order_by(DocumentChunkRow.ordinal)
            ).all()
            return [_chunk_model(row) for row in rows]

    def list_approved_chunks(self, project_id: str) -> list[DocumentChunk]:
        """Return chunks only from documents approved for this project."""

        project_id = validate_identifier(project_id)
        with Session(self._engine) as session:
            if session.get(ProjectRow, project_id) is None:
                raise LiteratureRepositoryError(f"project {project_id!r} was not found")
            rows = session.scalars(
                select(DocumentChunkRow)
                .join(
                    ProjectDocumentRow,
                    ProjectDocumentRow.document_id == DocumentChunkRow.document_id,
                )
                .where(
                    ProjectDocumentRow.project_id == project_id,
                    ProjectDocumentRow.status == "approved",
                )
                .order_by(DocumentChunkRow.document_id, DocumentChunkRow.ordinal)
            ).all()
            return [_chunk_model(row) for row in rows]

    def get_approved_chunk(self, project_id: str, chunk_id: str) -> tuple[DocumentChunk, Document]:
        """Load a Chunk and its Document only through an approved project link."""

        project_id = validate_identifier(project_id)
        chunk_id = validate_identifier(chunk_id)
        with Session(self._engine) as session:
            result = session.execute(
                select(DocumentChunkRow, DocumentRow)
                .join(DocumentRow, DocumentRow.document_id == DocumentChunkRow.document_id)
                .join(
                    ProjectDocumentRow,
                    ProjectDocumentRow.document_id == DocumentChunkRow.document_id,
                )
                .where(
                    DocumentChunkRow.chunk_id == chunk_id,
                    ProjectDocumentRow.project_id == project_id,
                    ProjectDocumentRow.status == "approved",
                )
            ).one_or_none()
            if result is None:
                raise ProjectDocumentConflictError(
                    "chunk must belong to an approved project document"
                )
            chunk_row, document_row = result
            return _chunk_model(chunk_row), _document_model(document_row)

    def list_project_documents(self, project_id: str) -> list[ProjectDocument]:
        project_id = validate_identifier(project_id)
        with Session(self._engine) as session:
            if session.get(ProjectRow, project_id) is None:
                raise LiteratureRepositoryError(f"project {project_id!r} was not found")
            rows = session.scalars(
                select(ProjectDocumentRow)
                .where(ProjectDocumentRow.project_id == project_id)
                .order_by(ProjectDocumentRow.created_at, ProjectDocumentRow.document_id)
            ).all()
            return [_project_document_model(row) for row in rows]


def document_id_for_content(content_sha256: str) -> str:
    """Derive a stable, non-sensitive catalog ID from a file hash."""

    if len(content_sha256) != 64 or any(char not in "0123456789abcdef" for char in content_sha256):
        raise ValueError("content_sha256 must be lowercase hexadecimal SHA-256")
    return f"doc_{content_sha256[:32]}"


def project_document_id_for(project_id: str, document_id: str) -> str:
    project_id = validate_identifier(project_id)
    document_id = validate_identifier(document_id)
    digest = hashlib.sha256(f"{project_id}\0{document_id}".encode()).hexdigest()[:32]
    return f"pd_{digest}"


def _document_model(row: DocumentRow) -> Document:
    from scholartrace.schemas import DocumentMetadata

    return Document.model_validate(
        {
            "document_id": row.document_id,
            "content_sha256": row.content_sha256,
            "mime_type": row.mime_type,
            "byte_size": row.byte_size,
            "source_type": row.source_type,
            "ingest_status": row.ingest_status,
            "quality_status": row.quality_status,
            "searchable": row.searchable,
            "metadata": DocumentMetadata.model_validate(
                {
                    "title": row.title,
                    "authors": row.authors,
                    "abstract": row.abstract,
                    "year": row.year,
                    "doi": row.doi,
                    "url": row.url,
                }
            ),
            "storage_relpath": row.storage_relpath,
            "text_relpath": row.text_relpath,
            "parser_version": row.parser_version,
            "created_at": row.created_at,
        }
    )


def _project_document_model(row: ProjectDocumentRow) -> ProjectDocument:
    return ProjectDocument.model_validate(
        {
            "project_document_id": row.project_document_id,
            "project_id": row.project_id,
            "document_id": row.document_id,
            "status": row.status,
            "relevance_score": row.relevance_score,
            "relevance_reason": row.relevance_reason,
            "decided_by": row.decided_by,
            "decided_at": row.decided_at,
            "created_at": row.created_at,
        }
    )


def _chunk_model(row: DocumentChunkRow) -> DocumentChunk:
    return DocumentChunk.model_validate(
        {
            "chunk_id": row.chunk_id,
            "document_id": row.document_id,
            "ordinal": row.ordinal,
            "text": row.text,
            "start_offset": row.start_offset,
            "end_offset": row.end_offset,
            "content_sha256": row.content_sha256,
            "created_at": row.created_at,
        }
    )
