from pathlib import Path

import httpx
import pytest

from scholartrace.literature.providers import (
    CrossrefClient,
    LiteratureMetadataService,
    OpenAlexClient,
    metadata_document_from_lookup,
)


def test_crossref_client_normalizes_verified_metadata_without_network() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.crossref.org"
        assert request.url.path == "/works"
        return httpx.Response(
            200,
            json={
                "message": {
                    "items": [
                        {
                            "title": ["Lychee disease detection"],
                            "author": [{"given": "Wei", "family": "Zhang"}],
                            "published-print": {"date-parts": [[2024, 5, 1]]},
                            "DOI": "10.1000/lychee.1",
                            "URL": "https://doi.org/10.1000/lychee.1",
                            "abstract": "<jats:p>Verified abstract.</jats:p>",
                        }
                    ]
                }
            },
            request=request,
        )

    result = CrossrefClient(transport=httpx.MockTransport(handler)).search("  lychee  ")
    assert result.status == "ok"
    assert result.metadata is not None
    assert result.metadata.title == "Lychee disease detection"
    assert result.metadata.authors == ["Wei Zhang"]
    assert result.metadata.year == 2024
    assert result.metadata.doi == "10.1000/lychee.1"
    assert result.metadata.abstract == "Verified abstract."


def test_openalex_client_reconstructs_abstract_and_metadata_document() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.openalex.org"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "Orchard vision",
                        "authorships": [{"author": {"display_name": "Li Wang"}}],
                        "publication_year": 2023,
                        "doi": "https://doi.org/10.2000/orchard.2",
                        "primary_location": {"landing_page_url": "https://example.org/orchard"},
                        "abstract_inverted_index": {"vision": [1], "orchard": [0]},
                    }
                ]
            },
            request=request,
        )

    result = OpenAlexClient(transport=httpx.MockTransport(handler)).search("orchard")
    assert result.status == "ok"
    assert result.metadata is not None
    assert result.metadata.abstract == "orchard vision"
    document = metadata_document_from_lookup(result)
    assert document is not None
    assert document.source_type == "openalex"
    assert document.ingest_status == "metadata_only"
    assert document.storage_relpath is None
    assert document.searchable is True


def test_metadata_service_falls_back_and_preserves_provider_failures() -> None:
    crossref = CrossrefClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(503, request=request))
    )

    def openalex_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"results": [{"title": "Fallback title", "publication_year": 2022}]},
            request=request,
        )

    service = LiteratureMetadataService(
        [crossref, OpenAlexClient(transport=httpx.MockTransport(openalex_handler))]
    )
    bundle = service.lookup("fallback")
    assert bundle.status == "ok"
    assert [attempt.status for attempt in bundle.attempts] == ["unavailable", "ok"]
    assert bundle.metadata is not None
    assert bundle.metadata.title == "Fallback title"


def test_metadata_failure_never_creates_invented_document(tmp_path: Path) -> None:
    unavailable = CrossrefClient(
        transport=httpx.MockTransport(
            lambda request: (_ for _ in ()).throw(httpx.ConnectError("offline", request=request))
        )
    )
    result = unavailable.search("known paper")
    assert result.status == "unavailable"
    assert result.metadata is None
    assert metadata_document_from_lookup(result) is None

    with pytest.raises(ValueError, match="must not be blank"):
        unavailable.search("   ")
