"""Transactional persistence for verified, source-linked evidence cards."""

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from scholartrace.identifiers import validate_identifier
from scholartrace.persistence.database import create_sqlite_engine
from scholartrace.persistence.models import EvidenceCardRow, ProjectRow
from scholartrace.schemas import EvidenceCard


class EvidenceRepositoryError(RuntimeError):
    """Base error for evidence-card persistence."""


class EvidenceCardConflictError(EvidenceRepositoryError):
    """Raised when a stable evidence-card identity is reused with new content."""


class EvidenceRepository:
    """Persist only cards that have already passed source validation."""

    def __init__(self, database_path: Path) -> None:
        self._engine = create_sqlite_engine(database_path)

    def close(self) -> None:
        self._engine.dispose()

    def save_card(self, card: EvidenceCard) -> EvidenceCard:
        with Session(self._engine) as session, session.begin():
            if session.get(ProjectRow, card.project_id) is None:
                raise EvidenceRepositoryError(f"project {card.project_id!r} was not found")
            existing = session.get(EvidenceCardRow, card.evidence_card_id)
            if existing is not None:
                persisted = _evidence_card_model(existing)
                if persisted.model_dump(exclude={"created_at"}) != card.model_dump(
                    exclude={"created_at"}
                ):
                    raise EvidenceCardConflictError(
                        f"evidence_card_id {card.evidence_card_id!r} has different content"
                    )
                return persisted
            row = EvidenceCardRow(
                evidence_card_id=card.evidence_card_id,
                project_id=card.project_id,
                document_id=card.source_span.document_id,
                chunk_id=card.source_span.chunk_id,
                statement=card.statement,
                quote=card.source_span.quote,
                source_start_offset=card.source_span.start_offset,
                source_end_offset=card.source_span.end_offset,
                locator_kind=card.locator_kind,
                locator_value=card.locator_value,
                verification_status=card.verification_status,
                verified_by=card.verified_by,
                created_at=card.created_at.replace(tzinfo=None),
            )
            session.add(row)
            try:
                session.flush()
            except IntegrityError as error:
                raise EvidenceCardConflictError(
                    "evidence card identity is already persisted"
                ) from error
            return _evidence_card_model(row)

    def list_project_cards(self, project_id: str) -> list[EvidenceCard]:
        project_id = validate_identifier(project_id)
        with Session(self._engine) as session:
            if session.get(ProjectRow, project_id) is None:
                raise EvidenceRepositoryError(f"project {project_id!r} was not found")
            rows = session.scalars(
                select(EvidenceCardRow)
                .where(EvidenceCardRow.project_id == project_id)
                .order_by(EvidenceCardRow.created_at, EvidenceCardRow.evidence_card_id)
            ).all()
            return [_evidence_card_model(row) for row in rows]


def _evidence_card_model(row: EvidenceCardRow) -> EvidenceCard:
    return EvidenceCard.model_validate(
        {
            "evidence_card_id": row.evidence_card_id,
            "project_id": row.project_id,
            "statement": row.statement,
            "source_span": {
                "document_id": row.document_id,
                "chunk_id": row.chunk_id,
                "quote": row.quote,
                "start_offset": row.source_start_offset,
                "end_offset": row.source_end_offset,
            },
            "locator_kind": row.locator_kind,
            "locator_value": row.locator_value,
            "verification_status": row.verification_status,
            "verified_by": row.verified_by,
            "created_at": row.created_at,
        }
    )
