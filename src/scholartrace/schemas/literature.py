"""Validated contracts for the independent literature catalog."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

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
ProjectDocumentStatus = Literal["candidate", "approved", "rejected"]


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
    relevance_score: float | None = Field(default=None, ge=0, le=1)
    relevance_reason: str | None = None
    decided_by: NonBlankText | None = None
    decided_at: datetime | None = None
    created_at: datetime


class DocumentChunk(BaseModel):
    """A traceable, searchable span of one catalog document."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: NonBlankText
    document_id: NonBlankText
    ordinal: int = Field(ge=0)
    text: str = Field(min_length=1)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(gt=0)
    content_sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    created_at: datetime

    @model_validator(mode="after")
    def validate_span(self) -> "DocumentChunk":
        if self.end_offset <= self.start_offset:
            raise ValueError("end_offset must be greater than start_offset")
        if not self.text.strip():
            raise ValueError("chunk text cannot be blank")
        if len(self.text) != self.end_offset - self.start_offset:
            raise ValueError("chunk offsets must span the exact chunk text length")
        return self


class ChunkSearchResult(BaseModel):
    """Hybrid retrieval result with the source span required for citation tracing."""

    model_config = ConfigDict(extra="forbid")

    chunk: DocumentChunk
    lexical_score: float = Field(ge=0)
    vector_score: float = Field(ge=0)
    score: float = Field(ge=0)
    index_generation: NonBlankText
