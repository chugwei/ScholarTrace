"""Validated domain contracts used by ScholarTrace workflows."""

from scholartrace.schemas.decisions import DecisionRecord
from scholartrace.schemas.design import (
    CaptureField,
    DataCollectionProtocol,
    PipelineSpec,
    PipelineStage,
)
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
    "CaptureField",
    "ChunkSearchResult",
    "DataCollectionProtocol",
    "DecisionRecord",
    "Document",
    "DocumentChunk",
    "DocumentMetadata",
    "EvidenceCard",
    "PipelineSpec",
    "PipelineStage",
    "ProjectDocument",
    "ResearchQuestion",
    "SourceSpan",
]
