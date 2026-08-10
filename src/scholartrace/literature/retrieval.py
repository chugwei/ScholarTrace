"""Local hybrid BM25/vector retrieval with atomic index replacement."""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scholartrace.identifiers import validate_identifier
from scholartrace.schemas import ChunkSearchResult, DocumentChunk

if TYPE_CHECKING:
    from scholartrace.persistence.literature_repository import LiteratureRepository

_TOKEN_PATTERN = re.compile(r"[\w]+", re.UNICODE)


class EmbeddingProvider(Protocol):
    """Replaceable vector provider used by the local index."""

    @property
    def name(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    def embed(self, text: str) -> list[float]: ...


class HashingEmbeddingProvider:
    """Deterministic offline vectorizer for tests and local-first deployments."""

    def __init__(self, dimensions: int = 64) -> None:
        if dimensions < 2:
            raise ValueError("dimensions must be at least 2")
        self._dimensions = dimensions

    @property
    def name(self) -> str:
        return "hashing-v1"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self._dimensions
        for token in _tokens(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self._dimensions
            vector[index] += 1.0
        return vector


class HybridIndexError(RuntimeError):
    """Base error for hybrid index operations."""


class IndexNotFoundError(HybridIndexError):
    """Raised when a project has not been indexed yet."""


class IndexCompatibilityError(HybridIndexError):
    """Raised when a stored index cannot be queried by the active provider."""


class IndexSnapshot(BaseModel):
    """Validated on-disk representation of one project chunk index."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(default=1, ge=1)
    project_id: str = Field(min_length=1)
    generation: str = Field(min_length=1)
    embedding_provider: str = Field(min_length=1)
    dimensions: int = Field(gt=0)
    chunks: list[DocumentChunk]
    term_frequencies: list[dict[str, int]]
    document_frequency: dict[str, int]
    average_document_length: float = Field(ge=0)
    vectors: list[list[float]]

    @model_validator(mode="after")
    def validate_alignment(self) -> IndexSnapshot:
        count = len(self.chunks)
        if len(self.term_frequencies) != count or len(self.vectors) != count:
            raise ValueError("index arrays must align with chunks")
        if any(len(vector) != self.dimensions for vector in self.vectors):
            raise ValueError("stored vector dimensions do not match the provider")
        return self


class HybridChunkIndex:
    """Persist one atomic hybrid index file per project."""

    def __init__(self, root: Path, embedding_provider: EmbeddingProvider | None = None) -> None:
        self.root = root.expanduser().resolve()
        self.embedding_provider = embedding_provider or HashingEmbeddingProvider()

    def rebuild(self, project_id: str, chunks: list[DocumentChunk]) -> IndexSnapshot:
        """Build a candidate snapshot and replace the active file only after success."""

        project_id = validate_identifier(project_id)
        if not chunks:
            raise HybridIndexError("cannot build an empty chunk index")
        ordered = sorted(chunks, key=lambda chunk: (chunk.document_id, chunk.ordinal))
        if len({chunk.chunk_id for chunk in ordered}) != len(ordered):
            raise HybridIndexError("chunk IDs must be unique in an index")
        snapshot = _build_snapshot(project_id, ordered, self.embedding_provider)

        path = self._path(project_id)
        temporary = path.with_name(f"{path.name}.tmp")
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(
                snapshot.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            with temporary.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
            temporary.replace(path)
        except Exception:
            if temporary.exists():
                temporary.unlink()
            raise
        return snapshot

    def rebuild_project(self, project_id: str, repository: LiteratureRepository) -> IndexSnapshot:
        """Index only chunks attached to explicitly approved project documents."""

        return self.rebuild(project_id, repository.list_approved_chunks(project_id))

    def load(self, project_id: str) -> IndexSnapshot:
        project_id = validate_identifier(project_id)
        path = self._path(project_id)
        if not path.exists():
            raise IndexNotFoundError(f"project index {project_id!r} was not found")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return IndexSnapshot.model_validate(payload)
        except Exception as error:
            raise HybridIndexError(f"project index {project_id!r} is invalid") from error

    def search(
        self,
        project_id: str,
        query: str,
        *,
        top_k: int = 5,
        lexical_weight: float = 0.5,
        vector_weight: float = 0.5,
    ) -> list[ChunkSearchResult]:
        """Return traceable results using BM25 and cosine similarity together."""

        if top_k < 1:
            raise ValueError("top_k must be positive")
        if lexical_weight < 0 or vector_weight < 0 or lexical_weight + vector_weight <= 0:
            raise ValueError("at least one retrieval weight must be positive")
        if not query.strip():
            return []
        snapshot = self.load(project_id)
        if (
            snapshot.embedding_provider != self.embedding_provider.name
            or snapshot.dimensions != self.embedding_provider.dimensions
        ):
            raise IndexCompatibilityError("stored index does not match the active vector provider")

        query_terms = _tokens(query)
        query_vector = _checked_vector(self.embedding_provider.embed(query), snapshot.dimensions)
        lexical_scores = [
            _bm25_score(
                query_terms,
                frequencies,
                snapshot.document_frequency,
                len(snapshot.chunks),
                snapshot.average_document_length,
            )
            for frequencies in snapshot.term_frequencies
        ]
        vector_scores = [
            max(0.0, _cosine_similarity(query_vector, vector)) for vector in snapshot.vectors
        ]
        lexical_max = max(lexical_scores, default=0.0)
        vector_max = max(vector_scores, default=0.0)
        combined = [
            lexical_weight * (lexical / lexical_max if lexical_max else 0.0)
            + vector_weight * (vector / vector_max if vector_max else 0.0)
            for lexical, vector in zip(lexical_scores, vector_scores, strict=True)
        ]
        ranked = sorted(
            range(len(snapshot.chunks)),
            key=lambda index: (-combined[index], snapshot.chunks[index].chunk_id),
        )
        return [
            ChunkSearchResult(
                chunk=snapshot.chunks[index],
                lexical_score=round(lexical_scores[index], 6),
                vector_score=round(vector_scores[index], 6),
                score=round(combined[index], 6),
                index_generation=snapshot.generation,
            )
            for index in ranked[:top_k]
            if combined[index] > 0
        ]

    def _path(self, project_id: str) -> Path:
        return self.root / f"{validate_identifier(project_id)}.hybrid.json"


def _build_snapshot(
    project_id: str,
    chunks: list[DocumentChunk],
    provider: EmbeddingProvider,
) -> IndexSnapshot:
    term_frequencies = [_term_frequency(chunk.text) for chunk in chunks]
    document_frequency: dict[str, int] = {}
    for frequencies in term_frequencies:
        for token in frequencies:
            document_frequency[token] = document_frequency.get(token, 0) + 1
    lengths = [sum(frequencies.values()) for frequencies in term_frequencies]
    vectors = [_checked_vector(provider.embed(chunk.text), provider.dimensions) for chunk in chunks]
    base_payload = {
        "project_id": project_id,
        "embedding_provider": provider.name,
        "dimensions": provider.dimensions,
        "chunks": [chunk.model_dump(mode="json") for chunk in chunks],
        "term_frequencies": term_frequencies,
        "document_frequency": document_frequency,
        "average_document_length": sum(lengths) / len(lengths),
        "vectors": vectors,
    }
    generation = hashlib.sha256(
        json.dumps(base_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()[:16]
    return IndexSnapshot(generation=generation, **base_payload)


def _tokens(text: str) -> list[str]:
    return [token.casefold() for token in _TOKEN_PATTERN.findall(text) if token.strip()]


def _term_frequency(text: str) -> dict[str, int]:
    frequencies: dict[str, int] = {}
    for token in _tokens(text):
        frequencies[token] = frequencies.get(token, 0) + 1
    return frequencies


def _bm25_score(
    query_terms: list[str],
    frequencies: dict[str, int],
    document_frequency: dict[str, int],
    document_count: int,
    average_document_length: float,
) -> float:
    if not query_terms:
        return 0.0
    k1 = 1.2
    b = 0.75
    document_length = sum(frequencies.values())
    score = 0.0
    for term in query_terms:
        term_frequency = frequencies.get(term, 0)
        if not term_frequency:
            continue
        df = document_frequency.get(term, 0)
        idf = math.log(1 + (document_count - df + 0.5) / (df + 0.5))
        denominator = term_frequency + k1 * (
            1 - b + b * document_length / max(average_document_length, 1e-12)
        )
        score += idf * (term_frequency * (k1 + 1)) / denominator
    return score


def _checked_vector(values: list[float], dimensions: int) -> list[float]:
    vector = [float(value) for value in values]
    if len(vector) != dimensions or not all(math.isfinite(value) for value in vector):
        raise HybridIndexError("embedding provider returned an invalid vector")
    return vector


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)
