"""Validated domain contracts used by ScholarTrace workflows."""

from scholartrace.schemas.algorithm import (
    AlgorithmComponent,
    AlgorithmSpec,
    CandidateExperimentPlan,
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
from scholartrace.schemas.experiment import (
    ClaimUpdate,
    ExperimentMatrixEntry,
    ExperimentPlan,
    MetricAggregate,
    MetricResult,
    RunManifest,
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
    "CandidateExperimentPlan",
    "CaptureField",
    "ChunkSearchResult",
    "ClaimUpdate",
    "DataCollectionProtocol",
    "DecisionRecord",
    "DesignFinding",
    "DesignValidationReport",
    "Document",
    "DocumentChunk",
    "DocumentMetadata",
    "EvidenceCard",
    "ExperimentMatrixEntry",
    "ExperimentPlan",
    "InnovationCandidate",
    "InnovationCandidateRanking",
    "InnovationFinding",
    "InnovationValidationReport",
    "MethodDifference",
    "MetricAggregate",
    "MetricResult",
    "PipelineSpec",
    "PipelineStage",
    "PipelineVersionComparison",
    "PriorArtEntry",
    "PriorArtMap",
    "ProjectDocument",
    "ResearchQuestion",
    "RunManifest",
    "SourceSpan",
]
