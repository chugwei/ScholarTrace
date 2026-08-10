"""Validated contracts for the independent literature catalog."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

DocumentSourceType = Literal["uploaded_pdf", "crossref", "openalex", "manual"]
DocumentIngestStatus = Literal["indexed", "failed", "metadata_only"]
DocumentQualityStatus = Literal[
    "ok",
    "empty_text",
    "parse_failed",
    "metadata_incomplete",
    "unknown",
]
ProjectDocumentStatus = Literal["candidate"]


class DocumentMetadata(BaseModel):
    """Metadata that can be verified independently of a full-text file."""

    model_config = ConfigDict(extra="forbid")

    title: NonBlankText | None = None
    authors: list[NonBlankText] = Field(default_factory=list)
    abstract: str | None = None
    year: int | None = Field(default=None, ge=1000, le=3000)
    doi: NonBlankText | None = None
    url: NonBlankText | None = None


class Document(BaseModel):
    """One global literature entry, independent from project membership."""

    model_config = ConfigDict(extra="forbid")

    document_id: NonBlankText
    content_sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    mime_type: NonBlankText
    byte_size: int = Field(ge=0)
    source_type: DocumentSourceType
    ingest_status: DocumentIngestStatus
    quality_status: DocumentQualityStatus
    searchable: bool
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    storage_relpath: NonBlankText | None = None
    text_relpath: NonBlankText | None = None
    parser_version: NonBlankText | None = None
    created_at: datetime


class ProjectDocument(BaseModel):
    """Project-specific candidate link; it is not global evidence approval."""

    model_config = ConfigDict(extra="forbid")

    project_document_id: NonBlankText
    project_id: NonBlankText
    document_id: NonBlankText
    status: ProjectDocumentStatus = "candidate"
    created_at: datetime
