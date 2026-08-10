"""Evidence-card creation with project approval and citation-source gates."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

from scholartrace.identifiers import validate_identifier
from scholartrace.persistence.evidence_repository import EvidenceRepository
from scholartrace.persistence.literature_repository import LiteratureRepository
from scholartrace.persistence.migrations import upgrade_database
from scholartrace.persistence.models import utc_now_naive
from scholartrace.schemas import Document, EvidenceCard, SourceSpan

_DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)


class EvidenceValidationError(ValueError):
    """Raised when a source-linked evidence card cannot be verified."""


class EvidenceCardService:
    """Create verified cards from approved chunks and independently locatable sources."""

    def __init__(self, database_path: Path, source_text_root: Path | None = None) -> None:
        upgrade_database(database_path)
        self._literature = LiteratureRepository(database_path)
        self._evidence = EvidenceRepository(database_path)
        self._source_text_root = (
            source_text_root.expanduser().resolve() if source_text_root else None
        )

    def close(self) -> None:
        self._literature.close()
        self._evidence.close()

    def create_card(
        self,
        project_id: str,
        chunk_id: str,
        *,
        statement: str,
        quote: str,
        verified_by: str,
    ) -> EvidenceCard:
        """Validate a quote and citation before persisting one verified card."""

        project_id = validate_identifier(project_id)
        chunk_id = validate_identifier(chunk_id)
        verified_by = validate_identifier(verified_by)
        if not statement.strip():
            raise EvidenceValidationError("evidence statement is required")
        if not quote.strip():
            raise EvidenceValidationError("source quote is required")

        chunk, document = self._literature.get_approved_chunk(project_id, chunk_id)
        relative_start = chunk.text.find(quote)
        if relative_start < 0:
            raise EvidenceValidationError("source quote is not present in the approved chunk")
        start_offset = chunk.start_offset + relative_start
        end_offset = start_offset + len(quote)
        locator_kind, locator_value = citation_locator_for(document)
        self._verify_runtime_source(document, start_offset, end_offset, quote)

        card = EvidenceCard(
            evidence_card_id=evidence_card_id_for(
                project_id,
                chunk_id,
                statement,
                start_offset,
                end_offset,
            ),
            project_id=project_id,
            statement=statement,
            source_span=SourceSpan(
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                quote=quote,
                start_offset=start_offset,
                end_offset=end_offset,
            ),
            locator_kind=locator_kind,
            locator_value=locator_value,
            verified_by=verified_by,
            created_at=utc_now_naive(),
        )
        return self._evidence.save_card(card)

    def list_project_cards(self, project_id: str) -> list[EvidenceCard]:
        return self._evidence.list_project_cards(project_id)

    def _verify_runtime_source(
        self, document: Document, start_offset: int, end_offset: int, quote: str
    ) -> None:
        if self._source_text_root is None or document.text_relpath is None:
            return
        text_path = (self._source_text_root / document.text_relpath).resolve()
        if not text_path.is_relative_to(self._source_text_root):
            raise EvidenceValidationError("source text path escapes the configured root")
        try:
            source_text = text_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise EvidenceValidationError("source text could not be read") from error
        if source_text[start_offset:end_offset] != quote:
            raise EvidenceValidationError("source quote does not match the runtime text artifact")


def citation_locator_for(document: Document) -> tuple[str, str]:
    """Choose a syntactically verifiable DOI, URL, or safe relative local path."""

    if document.metadata.doi:
        doi = document.metadata.doi.strip()
        if _DOI_PATTERN.fullmatch(doi):
            return "doi", doi
    if document.metadata.url:
        url = document.metadata.url.strip()
        parsed = urlparse(url)
        if (
            parsed.scheme in {"http", "https"}
            and parsed.netloc
            and not any(char.isspace() for char in url)
        ):
            return "url", url
    for candidate in (document.text_relpath, document.storage_relpath):
        if candidate and _is_safe_relative_path(candidate):
            return "local", candidate
    raise EvidenceValidationError("document has no valid DOI, URL, or local source path")


def evidence_card_id_for(
    project_id: str,
    chunk_id: str,
    statement: str,
    start_offset: int,
    end_offset: int,
) -> str:
    """Derive an idempotent card ID from its project, span, and statement."""

    digest = hashlib.sha256(
        f"{project_id}\0{chunk_id}\0{statement}\0{start_offset}\0{end_offset}".encode()
    ).hexdigest()
    return f"evidence_{digest[:32]}"


def _is_safe_relative_path(value: str) -> bool:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    return bool(normalized.strip()) and not path.is_absolute() and ".." not in path.parts
