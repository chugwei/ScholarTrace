"""Deterministic, offset-preserving text chunking for catalog documents."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from scholartrace.identifiers import validate_identifier
from scholartrace.schemas import DocumentChunk


def chunk_id_for(document_id: str, ordinal: int, text: str) -> str:
    """Derive a stable chunk ID from its document, position, and exact text."""

    document_id = validate_identifier(document_id)
    if ordinal < 0:
        raise ValueError("ordinal must be non-negative")
    digest = hashlib.sha256(f"{document_id}\0{ordinal}\0{text}".encode()).hexdigest()
    return f"chunk_{digest[:32]}"


def chunk_document_text(
    document_id: str,
    text: str,
    *,
    max_chars: int = 800,
    overlap_chars: int | None = None,
    created_at: datetime | None = None,
) -> list[DocumentChunk]:
    """Split text into deterministic overlapping chunks without losing offsets."""

    document_id = validate_identifier(document_id)
    if max_chars < 1:
        raise ValueError("max_chars must be positive")
    if overlap_chars is None:
        overlap_chars = min(120, max_chars // 5)
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be non-negative and smaller than max_chars")
    if not text:
        return []

    timestamp = created_at or datetime.now(UTC).replace(tzinfo=None)
    chunks: list[DocumentChunk] = []
    start = 0
    ordinal = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        span = text[start:end]
        if span.strip():
            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id_for(document_id, ordinal, span),
                    document_id=document_id,
                    ordinal=ordinal,
                    text=span,
                    start_offset=start,
                    end_offset=end,
                    content_sha256=hashlib.sha256(span.encode("utf-8")).hexdigest(),
                    created_at=timestamp,
                )
            )
            ordinal += 1
        if end == len(text):
            break
        start = end - overlap_chars
    return chunks
