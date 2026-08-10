"""Validated domain contracts used by ScholarTrace workflows."""

from scholartrace.schemas.decisions import DecisionRecord
from scholartrace.schemas.design import (
    CaptureField,
    DataCollectionProtocol,
    DesignFinding,
    DesignValidationReport,
    PipelineSpec,
    PipelineStage,
    PipelineVersionComparison,
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
    "DesignFinding",
    "DesignValidationReport",
    "Document",
    "DocumentChunk",
    "DocumentMetadata",
    "EvidenceCard",
    "PipelineSpec",
    "PipelineStage",
    "PipelineVersionComparison",
    "ProjectDocument",
    "ResearchQuestion",
    "SourceSpan",
]
