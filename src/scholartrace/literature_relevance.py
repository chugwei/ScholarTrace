"""Deterministic document-level relevance scoring for project candidates."""

from __future__ import annotations

import re
from dataclasses import dataclass

from scholartrace.schemas import Document

_TOKEN_PATTERN = re.compile(r"[\w]+", re.UNICODE)


@dataclass(frozen=True, slots=True)
class RelevanceScore:
    document: Document
    score: float
    matched_terms: tuple[str, ...]
    reason: str


def score_document_relevance(query: str, document: Document) -> RelevanceScore:
    """Score metadata overlap without claiming semantic relevance or evidence."""

    query_terms = _tokens(query)
    searchable = " ".join(
        value
        for value in [
            document.metadata.title,
            " ".join(document.metadata.authors),
            document.metadata.abstract,
            document.metadata.doi,
        ]
        if value
    )
    document_terms = _tokens(searchable)
    matched = tuple(sorted(query_terms & document_terms))
    score = 0.0 if not query_terms else round(len(matched) / len(query_terms), 6)
    reason = (
        f"metadata term overlap {len(matched)}/{len(query_terms)}"
        if query_terms
        else "blank query has no relevance terms"
    )
    return RelevanceScore(document=document, score=score, matched_terms=matched, reason=reason)


def _tokens(value: str) -> set[str]:
    return {token.casefold() for token in _TOKEN_PATTERN.findall(value) if token.strip()}
