from datetime import UTC, datetime

import pytest

from scholartrace.manuscript import (
    SectionGenerationError,
    generate_section_draft,
    parse_bibtex,
    validate_manuscript_consistency,
)
from scholartrace.schemas import Claim, MetricResult, SectionContract

BIBTEX = """
@article{li2024,
  author = {Li, Wei},
  title = {A reliable study},
  year = {2024}
}
"""
CREATED_AT = datetime(2026, 8, 11, tzinfo=UTC)


def verified_metric(*, value: float = 0.9, metric_id: str = "metric-m10") -> MetricResult:
    return MetricResult(
        metric_result_id=metric_id,
        project_id="lychee-m10",
        run_id="run-m10",
        name="accuracy",
        split="validation",
        value=value,
        source="independent_recompute",
        verification_status="verified",
        is_final=True,
        data_version="sha256:data-m10",
        evaluation_script_sha256="a" * 64,
        created_at=CREATED_AT,
    )


def result_claim(*, claim_id: str = "claim-result") -> Claim:
    return Claim(
        claim_id=claim_id,
        project_id="lychee-m10",
        text="The proposed method reached the verified accuracy.",
        claim_type="result",
        status="supported",
        metric_result_ids=["metric-m10"],
        manuscript_locations=["abstract", "results", "conclusion"],
        created_by="researcher-001",
        created_at=CREATED_AT,
    )


def test_consistency_passes_for_source_markers_and_matching_sections() -> None:
    marker = "{{claim:claim-result}} {{metric:metric-m10 value=0.9}} [@li2024]"
    report = validate_manuscript_consistency(
        {"abstract": marker, "results": marker, "conclusion": marker},
        claims=[result_claim()],
        metrics=[verified_metric()],
        bibliography=parse_bibtex(BIBTEX),
    )
    assert report.status == "passed"
    assert report.citation_report.status == "passed"
    assert report.numeric_mismatches == []


def test_consistency_reports_number_drift_and_new_conclusion_claim() -> None:
    report = validate_manuscript_consistency(
        {
            "abstract": "{{claim:claim-result}} {{metric:metric-m10 value=0.9}}",
            "results": "{{claim:claim-result}} {{metric:metric-m10 value=0.9}}",
            "conclusion": "{{claim:claim-new}} {{metric:metric-m10 value=0.8}}",
        },
        claims=[result_claim(), result_claim(claim_id="claim-new")],
        metrics=[verified_metric()],
        bibliography=[],
    )
    assert report.status == "failed"
    assert report.conclusion_new_claim_ids == ["claim-new"]
    assert any("cross-section:metric-m10" in item for item in report.numeric_mismatches)


def test_consistency_lists_insufficient_and_unbound_sources() -> None:
    gap = Claim(
        claim_id="claim-gap",
        project_id="lychee-m10",
        text="The evidence is not available.",
        claim_type="limitation",
        status="insufficient",
        created_by="researcher-001",
    )
    report = validate_manuscript_consistency(
        {
            "results": "{{claim:claim-gap}} {{metric:metric-missing value=1.0}}",
        },
        claims=[gap],
        metrics=[verified_metric()],
        bibliography=[],
    )
    assert report.status == "failed"
    assert report.missing_evidence == ["claim-gap:insufficient"]
    assert report.unbound_metric_markers == ["results:metric-missing"]


def test_generator_emits_verified_metric_marker_and_rejects_unverified_metric() -> None:
    contract = SectionContract(
        section_id="section-results",
        manuscript_id="ms-m10-v1",
        section="results",
        purpose="Report verified metrics.",
        required_claim_ids=["claim-result"],
        required_metric_result_ids=["metric-m10"],
        created_by="researcher-001",
    )
    draft = generate_section_draft(
        contract,
        [result_claim()],
        metric_results=[verified_metric()],
    )
    assert "{{metric:metric-m10 value=0.90000000000000002}}" in draft.markdown
    assert draft.metric_result_ids == ["metric-m10"]
    with pytest.raises(SectionGenerationError, match="verified final"):
        generate_section_draft(
            contract,
            [result_claim()],
            metric_results=[verified_metric().model_copy(update={"is_final": False})],
        )
