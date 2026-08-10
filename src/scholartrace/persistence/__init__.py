"""SQLite persistence for ScholarTrace domain records."""

from scholartrace.persistence.design_repository import DesignRepository
from scholartrace.persistence.evidence_repository import EvidenceRepository
from scholartrace.persistence.figure_repository import FigureRepository
from scholartrace.persistence.manuscript_repository import ManuscriptRepository
from scholartrace.persistence.repository import ProjectRepository

__all__ = [
    "DesignRepository",
    "EvidenceRepository",
    "FigureRepository",
    "ManuscriptRepository",
    "ProjectRepository",
]
