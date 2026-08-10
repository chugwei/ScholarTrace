"""Independent literature ingestion and metadata providers."""

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
    "HashingEmbeddingProvider",
    "HybridChunkIndex",
    "HybridIndexError",
    "IndexCompatibilityError",
    "IndexNotFoundError",
    "LiteratureMetadataService",
    "MetadataLookupBundle",
    "MetadataLookupResult",
    "OpenAlexClient",
    "metadata_document_from_lookup",
]
