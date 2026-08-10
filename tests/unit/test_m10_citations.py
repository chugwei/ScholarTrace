import pytest

from scholartrace.manuscript import (
    BibTeXParseError,
    SectionGenerationError,
    extract_citation_keys,
    generate_section_draft,
    parse_bibtex,
    render_bibtex,
    validate_bibtex_citations,
)
from scholartrace.schemas import Claim, SectionContract

BIBTEX = """
@article{li2024,
  author = {Li, Wei and Chen, Ming},
  title = {A reliable study},
  year = {2024},
  doi = {https://doi.org/10.1000/reliable},
  journal = {Journal of Evidence}
}

@inproceedings{wang2023,
  author = "Wang, Li and Zhou, Hui",
  title = "A reproducible method",
  year = 2023,
  booktitle = {Proceedings of Testing}
}
"""


def test_bibtex_parser_normalizes_entries_and_renders_deterministically() -> None:
    entries = parse_bibtex(BIBTEX)
    assert [entry.citation_key for entry in entries] == ["li2024", "wang2023"]
    assert entries[0].authors == ["Li, Wei", "Chen, Ming"]
    assert entries[0].doi == "10.1000/reliable"
    rendered = render_bibtex(reversed(entries))
    assert rendered.index("li2024") < rendered.index("wang2023")
    assert "author = {Li, Wei and Chen, Ming}" in rendered


def test_citation_validation_reports_missing_keys_and_latex_forms() -> None:
    markdown = "The methods follow [@li2024; @missing] and \\citep{wang2023}."
    assert extract_citation_keys(markdown) == ["li2024", "missing", "wang2023"]
    report = validate_bibtex_citations(markdown, BIBTEX)
    assert report.status == "failed"
    assert report.resolved_keys == ["li2024", "wang2023"]
    assert report.missing_keys == ["missing"]


def test_invalid_bibtex_is_a_failed_report_and_not_silently_repaired() -> None:
    report = validate_bibtex_citations(
        "[@paper]", "@article{paper, title={No author}, year={2024}}"
    )
    assert report.status == "failed"
    assert report.parse_errors
    with pytest.raises(BibTeXParseError, match="missing"):
        parse_bibtex("@article{paper, title={No author}, year={2024}}")


def test_section_draft_preserves_claim_status_and_source_keys() -> None:
    contract = SectionContract(
        section_id="section-intro",
        manuscript_id="ms-m10-v1",
        section="introduction",
        purpose="Explain the evidence-backed gap.",
        required_claim_ids=["claim-gap"],
        required_citation_keys=["li2024"],
        created_by="researcher-001",
    )
    claim = Claim(
        claim_id="claim-gap",
        project_id="lychee-m10",
        text="Prior work leaves a traceability gap.",
        claim_type="literature",
        status="supported",
        evidence_ids=["evidence-001"],
        created_by="researcher-001",
    )
    draft = generate_section_draft(contract, [claim], bibliography=parse_bibtex(BIBTEX))
    assert draft.claim_ids == ["claim-gap"]
    assert draft.citation_keys == ["li2024"]
    assert "claim-gap" in draft.markdown
    assert "[@li2024]" in draft.markdown
    assert len(draft.content_sha256) == 64


def test_section_draft_blocks_missing_claim_or_citation() -> None:
    contract = SectionContract(
        section_id="section-results",
        manuscript_id="ms-m10-v1",
        section="results",
        purpose="Report only supported results.",
        required_claim_ids=["claim-result"],
        required_citation_keys=["missing"],
        created_by="researcher-001",
    )
    with pytest.raises(SectionGenerationError, match="missing claims"):
        generate_section_draft(contract, [], bibliography=parse_bibtex(BIBTEX))
    claim = Claim(
        claim_id="claim-result",
        project_id="lychee-m10",
        text="The verified metric is available.",
        claim_type="result",
        status="supported",
        metric_result_ids=["metric-m10"],
        created_by="researcher-001",
    )
    with pytest.raises(SectionGenerationError, match="missing citations"):
        generate_section_draft(contract, [claim], bibliography=parse_bibtex(BIBTEX))
