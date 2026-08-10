"""Evidence-bound manuscript, section, and claim contracts."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scholartrace.schemas.research import NonBlankText

ManuscriptStatus = Literal["draft", "in_review", "approved", "archived"]
ManuscriptTemplate = Literal[
    "journal_article",
    "conference_paper",
    "technical_report",
    "preprint",
]
SectionKey = Literal[
    "title",
    "abstract",
    "introduction",
    "related_work",
    "materials_data",
    "methods",
    "experiments",
    "results",
    "discussion",
    "conclusion",
    "references",
]
SectionContractStatus = Literal["draft", "ready", "blocked", "approved"]
ClaimType = Literal["literature", "method", "data", "result", "discussion", "limitation"]
ClaimStatus = Literal["planned", "supported", "contradicted", "insufficient", "withdrawn"]
BibTeXEntryType = Literal[
    "article",
    "book",
    "incollection",
    "inproceedings",
    "misc",
    "phdthesis",
    "techreport",
]


def _utc_now() -> datetime:
    return datetime.now(UTC)


class Manuscript(BaseModel):
    """A versioned manuscript container; section text is added in later batches."""

    model_config = ConfigDict(extra="forbid")

    manuscript_id: NonBlankText | None = None
    project_id: NonBlankText | None = None
    title: NonBlankText
    target_template: ManuscriptTemplate = "journal_article"
    version: int = Field(default=1, ge=1)
    parent_manuscript_id: NonBlankText | None = None
    status: ManuscriptStatus = "draft"
    section_ids: list[NonBlankText] = Field(default_factory=list)
    content_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    created_by: NonBlankText | None = None
    created_at: datetime = Field(default_factory=_utc_now)

    @model_validator(mode="after")
    def validate_unique_sections(self) -> "Manuscript":
        if len(self.section_ids) != len(set(self.section_ids)):
            raise ValueError("manuscript section_ids must be unique")
        return self


class SectionContract(BaseModel):
    """A bounded contract describing what a manuscript section may assert."""

    model_config = ConfigDict(extra="forbid")

    section_id: NonBlankText | None = None
    manuscript_id: NonBlankText | None = None
    section: SectionKey
    purpose: NonBlankText
    required_claim_ids: list[NonBlankText] = Field(default_factory=list)
    required_evidence_ids: list[NonBlankText] = Field(default_factory=list)
    required_metric_result_ids: list[NonBlankText] = Field(default_factory=list)
    required_figure_ids: list[NonBlankText] = Field(default_factory=list)
    required_citation_keys: list[NonBlankText] = Field(default_factory=list)
    allow_new_claims: bool = True
    word_limit: int | None = Field(default=None, ge=1)
    status: SectionContractStatus = "draft"
    content_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    created_by: NonBlankText | None = None
    created_at: datetime = Field(default_factory=_utc_now)

    @model_validator(mode="after")
    def validate_contract(self) -> "SectionContract":
        reference_lists = (
            self.required_claim_ids,
            self.required_evidence_ids,
            self.required_metric_result_ids,
            self.required_figure_ids,
            self.required_citation_keys,
        )
        if any(len(values) != len(set(values)) for values in reference_lists):
            raise ValueError("section contract references must be unique")
        if self.section == "conclusion" and self.allow_new_claims:
            raise ValueError("conclusion contracts cannot allow new claims")
        return self


class BibTeXEntry(BaseModel):
    """A parsed bibliography entry with the fields needed for citation checks."""

    model_config = ConfigDict(extra="forbid")

    citation_key: NonBlankText
    entry_type: BibTeXEntryType
    title: NonBlankText
    authors: list[NonBlankText] = Field(min_length=1)
    year: int = Field(ge=1000, le=2200)
    doi: NonBlankText | None = None
    url: NonBlankText | None = None
    journal: NonBlankText | None = None
    booktitle: NonBlankText | None = None
    publisher: NonBlankText | None = None
    source_document_id: NonBlankText | None = None


class CitationValidationReport(BaseModel):
    """Deterministic result of resolving manuscript citations."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["passed", "failed"]
    cited_keys: list[NonBlankText] = Field(default_factory=list)
    resolved_keys: list[NonBlankText] = Field(default_factory=list)
    missing_keys: list[NonBlankText] = Field(default_factory=list)
    duplicate_keys: list[NonBlankText] = Field(default_factory=list)
    parse_errors: list[NonBlankText] = Field(default_factory=list)


class SectionDraft(BaseModel):
    """A deterministic section draft with explicit source IDs."""

    model_config = ConfigDict(extra="forbid")

    section_id: NonBlankText
    manuscript_id: NonBlankText
    markdown: NonBlankText
    claim_ids: list[NonBlankText] = Field(default_factory=list)
    citation_keys: list[NonBlankText] = Field(default_factory=list)
    metric_result_ids: list[NonBlankText] = Field(default_factory=list)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generated_by: NonBlankText
    created_at: datetime = Field(default_factory=_utc_now)


class ManuscriptConsistencyReport(BaseModel):
    """Cross-section checks for claims, citations, and MetricResult markers."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["passed", "failed"]
    citation_report: CitationValidationReport
    checked_sections: list[NonBlankText] = Field(default_factory=list)
    missing_evidence: list[NonBlankText] = Field(default_factory=list)
    unsupported_claim_ids: list[NonBlankText] = Field(default_factory=list)
    missing_claim_ids: list[NonBlankText] = Field(default_factory=list)
    unbound_metric_markers: list[NonBlankText] = Field(default_factory=list)
    numeric_mismatches: list[NonBlankText] = Field(default_factory=list)
    conclusion_new_claim_ids: list[NonBlankText] = Field(default_factory=list)


class Claim(BaseModel):
    """A ledger entry whose status is bounded by explicit evidence references."""

    model_config = ConfigDict(extra="forbid")

    claim_id: NonBlankText | None = None
    project_id: NonBlankText | None = None
    text: NonBlankText
    claim_type: ClaimType
    status: ClaimStatus = "planned"
    evidence_ids: list[NonBlankText] = Field(default_factory=list)
    experiment_run_ids: list[NonBlankText] = Field(default_factory=list)
    metric_result_ids: list[NonBlankText] = Field(default_factory=list)
    manuscript_locations: list[NonBlankText] = Field(default_factory=list)
    content_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    created_by: NonBlankText | None = None
    created_at: datetime = Field(default_factory=_utc_now)

    @model_validator(mode="after")
    def validate_evidence_boundary(self) -> "Claim":
        references = self.evidence_ids + self.experiment_run_ids + self.metric_result_ids
        if len(references) != len(set(references)):
            raise ValueError("claim evidence references must be unique")
        if self.status == "supported" and not references:
            raise ValueError("supported claims require at least one evidence reference")
        if (
            self.claim_type == "result"
            and self.status == "supported"
            and not self.metric_result_ids
        ):
            raise ValueError("supported result claims require metric_result_ids")
        return self
