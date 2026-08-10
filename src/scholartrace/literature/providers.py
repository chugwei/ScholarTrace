"""Replaceable Crossref/OpenAlex metadata clients with explicit degradation."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Literal, Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field

from scholartrace.persistence.literature_repository import document_id_for_content
from scholartrace.schemas import Document, DocumentMetadata

MetadataProviderName = Literal["crossref", "openalex"]
MetadataLookupStatus = Literal["ok", "not_found", "unavailable"]


class MetadataLookupResult(BaseModel):
    """One provider attempt; unavailable never contains invented metadata."""

    model_config = ConfigDict(extra="forbid")

    provider: MetadataProviderName
    query: str
    status: MetadataLookupStatus
    metadata: DocumentMetadata | None = None
    error: str | None = None


class MetadataLookupBundle(BaseModel):
    """Ordered provider attempts and the first verified successful metadata."""

    model_config = ConfigDict(extra="forbid")

    query: str
    status: MetadataLookupStatus
    metadata: DocumentMetadata | None = None
    attempts: list[MetadataLookupResult] = Field(default_factory=list)


class MetadataProvider(Protocol):
    provider_name: MetadataProviderName

    def search(self, query: str) -> MetadataLookupResult: ...


class CrossrefClient:
    provider_name: MetadataProviderName = "crossref"

    def __init__(
        self,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._transport = transport
        self._timeout = timeout

    def search(self, query: str) -> MetadataLookupResult:
        query = _clean_query(query)
        try:
            with httpx.Client(
                transport=self._transport,
                timeout=self._timeout,
                headers={"User-Agent": "ScholarTrace/0.3.0"},
            ) as client:
                response = client.get(
                    "https://api.crossref.org/works",
                    params={"query.bibliographic": query, "rows": 1},
                )
                if response.status_code != 200:
                    return _unavailable(
                        self.provider_name, query, f"http_status_{response.status_code}"
                    )
                payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            return _unavailable(self.provider_name, query, type(error).__name__)
        item = _first_mapping(payload.get("message", {}).get("items"))
        if item is None:
            return _not_found(self.provider_name, query)
        metadata = _crossref_metadata(item)
        if metadata is None:
            return _not_found(self.provider_name, query)
        return MetadataLookupResult(
            provider=self.provider_name,
            query=query,
            status="ok",
            metadata=metadata,
        )


class OpenAlexClient:
    provider_name: MetadataProviderName = "openalex"

    def __init__(
        self,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._transport = transport
        self._timeout = timeout

    def search(self, query: str) -> MetadataLookupResult:
        query = _clean_query(query)
        try:
            with httpx.Client(
                transport=self._transport,
                timeout=self._timeout,
                headers={"User-Agent": "ScholarTrace/0.3.0"},
            ) as client:
                response = client.get(
                    "https://api.openalex.org/works",
                    params={"search": query, "per-page": 1},
                )
                if response.status_code != 200:
                    return _unavailable(
                        self.provider_name, query, f"http_status_{response.status_code}"
                    )
                payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            return _unavailable(self.provider_name, query, type(error).__name__)
        item = _first_mapping(payload.get("results"))
        if item is None:
            return _not_found(self.provider_name, query)
        metadata = _openalex_metadata(item)
        if metadata is None:
            return _not_found(self.provider_name, query)
        return MetadataLookupResult(
            provider=self.provider_name,
            query=query,
            status="ok",
            metadata=metadata,
        )


class LiteratureMetadataService:
    """Try explicit providers in order and preserve every failure reason."""

    def __init__(self, providers: Sequence[MetadataProvider]) -> None:
        self.providers = list(providers)

    def lookup(self, query: str) -> MetadataLookupBundle:
        query = _clean_query(query)
        attempts: list[MetadataLookupResult] = []
        for provider in self.providers:
            result = provider.search(query)
            attempts.append(result)
            if result.status == "ok":
                return MetadataLookupBundle(
                    query=query,
                    status="ok",
                    metadata=result.metadata,
                    attempts=attempts,
                )
        status: MetadataLookupStatus = (
            "not_found"
            if attempts and all(item.status == "not_found" for item in attempts)
            else "unavailable"
        )
        return MetadataLookupBundle(query=query, status=status, attempts=attempts)


def metadata_document_from_lookup(result: MetadataLookupResult) -> Document | None:
    """Build a searchable metadata-only Document without claiming a full text file."""

    if result.status != "ok" or result.metadata is None:
        return None
    canonical = json.dumps(
        {"provider": result.provider, "metadata": result.metadata.model_dump(mode="json")},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    content_sha256 = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return Document(
        document_id=document_id_for_content(content_sha256),
        content_sha256=content_sha256,
        mime_type="application/json",
        byte_size=0,
        source_type=result.provider,
        ingest_status="metadata_only",
        quality_status="ok"
        if result.metadata.title or result.metadata.doi
        else "metadata_incomplete",
        searchable=True,
        metadata=result.metadata,
        created_at=_utc_now_naive(),
    )


def _crossref_metadata(item: Mapping[str, object]) -> DocumentMetadata | None:
    title = _first_string(item.get("title"))
    authors = _crossref_authors(item.get("author"))
    year = _date_parts_year(item.get("published-print")) or _date_parts_year(
        item.get("published-online")
    )
    doi = _normalize_doi(item.get("DOI"))
    url = _string(item.get("URL"))
    abstract = _strip_tags(_string(item.get("abstract")))
    if not any([title, authors, year, doi, url, abstract]):
        return None
    return DocumentMetadata(
        title=title,
        authors=authors,
        year=year,
        doi=doi,
        url=url,
        abstract=abstract,
    )


def _openalex_metadata(item: Mapping[str, object]) -> DocumentMetadata | None:
    title = _string(item.get("title"))
    authors = _openalex_authors(item.get("authorships"))
    year = item.get("publication_year") if isinstance(item.get("publication_year"), int) else None
    doi = _normalize_doi(item.get("doi"))
    location = item.get("primary_location")
    url = _string(location.get("landing_page_url")) if isinstance(location, Mapping) else None
    abstract = _openalex_abstract(item.get("abstract_inverted_index"))
    if not any([title, authors, year, doi, url, abstract]):
        return None
    return DocumentMetadata(
        title=title,
        authors=authors,
        year=year,
        doi=doi,
        url=url,
        abstract=abstract,
    )


def _crossref_authors(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    authors: list[str] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        name = " ".join(
            part for part in [_string(item.get("given")), _string(item.get("family"))] if part
        )
        if name:
            authors.append(name)
    return authors


def _openalex_authors(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    authors: list[str] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        author = item.get("author")
        name = _string(author.get("display_name")) if isinstance(author, Mapping) else None
        if name:
            authors.append(name)
    return authors


def _openalex_abstract(value: object) -> str | None:
    if not isinstance(value, Mapping):
        return None
    words: list[tuple[int, str]] = []
    for token, positions in value.items():
        if not isinstance(token, str) or not isinstance(positions, list):
            continue
        words.extend((position, token) for position in positions if isinstance(position, int))
    return " ".join(word for _, word in sorted(words)) or None


def _date_parts_year(value: object) -> int | None:
    if not isinstance(value, Mapping):
        return None
    date_parts = value.get("date-parts")
    if not isinstance(date_parts, list) or not date_parts or not isinstance(date_parts[0], list):
        return None
    year = date_parts[0][0] if date_parts[0] else None
    return year if isinstance(year, int) else None


def _normalize_doi(value: object) -> str | None:
    doi = _string(value)
    if doi is None:
        return None
    return re.sub(r"^https?://doi\.org/", "", doi, flags=re.IGNORECASE).strip()


def _first_mapping(value: object) -> Mapping[str, object] | None:
    if isinstance(value, list) and value and isinstance(value[0], Mapping):
        return value[0]
    return None


def _first_string(value: object) -> str | None:
    if isinstance(value, list):
        return _string(value[0]) if value else None
    return _string(value)


def _string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _strip_tags(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"<[^>]+>", " ", value).strip() or None


def _clean_query(query: str) -> str:
    normalized = query.strip()
    if not normalized:
        raise ValueError("metadata query must not be blank")
    return normalized


def _not_found(provider: MetadataProviderName, query: str) -> MetadataLookupResult:
    return MetadataLookupResult(provider=provider, query=query, status="not_found")


def _unavailable(
    provider: MetadataProviderName,
    query: str,
    error: str,
) -> MetadataLookupResult:
    return MetadataLookupResult(provider=provider, query=query, status="unavailable", error=error)


def _utc_now_naive():
    from scholartrace.persistence.models import utc_now_naive

    return utc_now_naive()
