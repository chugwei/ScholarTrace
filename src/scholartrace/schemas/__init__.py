"""Validated domain contracts used by ScholarTrace workflows."""

from scholartrace.schemas.decisions import DecisionRecord
from scholartrace.schemas.literature import Document, DocumentMetadata, ProjectDocument
from scholartrace.schemas.research import ResearchQuestion

__all__ = [
    "DecisionRecord",
    "Document",
    "DocumentMetadata",
    "ProjectDocument",
    "ResearchQuestion",
]
