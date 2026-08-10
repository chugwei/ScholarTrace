"""Validated domain contracts used by ScholarTrace workflows."""

from scholartrace.schemas.algorithm import (
    AlgorithmComponent,
    AlgorithmSpec,
    InnovationCandidate,
    InnovationCandidateRanking,
    InnovationFinding,
    InnovationValidationReport,
    MethodDifference,
    PriorArtEntry,
    PriorArtMap,
)
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
    "AlgorithmComponent",
    "AlgorithmSpec",
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
    "InnovationCandidate",
    "InnovationCandidateRanking",
    "InnovationFinding",
    "InnovationValidationReport",
    "MethodDifference",
    "PipelineSpec",
    "PipelineStage",
    "PipelineVersionComparison",
    "PriorArtEntry",
    "PriorArtMap",
    "ProjectDocument",
    "ResearchQuestion",
    "SourceSpan",
]
