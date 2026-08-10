"""Validated domain contracts used by ScholarTrace workflows."""

from scholartrace.schemas.decisions import DecisionRecord
from scholartrace.schemas.literature import (
    ChunkSearchResult,
    Document,
    DocumentChunk,
    DocumentMetadata,
    EvidenceCard,
    ProjectDocument,
    SourceSpan,
)
from scholartrace.schemas.research import ResearchQuestion

__all__ = [
    "ChunkSearchResult",
    "DecisionRecord",
    "Document",
    "DocumentChunk",
    "DocumentMetadata",
    "EvidenceCard",
    "ProjectDocument",
    "ResearchQuestion",
    "SourceSpan",
]
