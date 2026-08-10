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

__all__ = [
    "CrossrefClient",
    "DocumentIngestError",
    "DocumentLibrary",
    "LiteratureMetadataService",
    "MetadataLookupBundle",
    "MetadataLookupResult",
    "OpenAlexClient",
    "metadata_document_from_lookup",
]
