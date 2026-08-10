"""Independent literature ingestion and metadata providers."""

from scholartrace.literature.evidence import (
    EvidenceCardService,
    EvidenceValidationError,
    citation_locator_for,
)
from scholartrace.literature.ingestion import DocumentIngestError, DocumentLibrary
from scholartrace.literature.providers import (
    CrossrefClient,
    LiteratureMetadataService,
    MetadataLookupBundle,
    MetadataLookupResult,
    OpenAlexClient,
    metadata_document_from_lookup,
)
from scholartrace.literature.retrieval import (
    EmbeddingProvider,
    HashingEmbeddingProvider,
    HybridChunkIndex,
    HybridIndexError,
    IndexCompatibilityError,
    IndexNotFoundError,
)

__all__ = [
    "CrossrefClient",
    "DocumentIngestError",
    "DocumentLibrary",
    "EmbeddingProvider",
    "EvidenceCardService",
    "EvidenceValidationError",
    "HashingEmbeddingProvider",
    "HybridChunkIndex",
    "HybridIndexError",
    "IndexCompatibilityError",
    "IndexNotFoundError",
    "LiteratureMetadataService",
    "MetadataLookupBundle",
    "MetadataLookupResult",
    "OpenAlexClient",
    "citation_locator_for",
    "metadata_document_from_lookup",
]
