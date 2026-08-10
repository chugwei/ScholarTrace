"""Deterministic section-draft generation from manuscript contracts."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

from scholartrace.schemas import BibTeXEntry, Claim, MetricResult, SectionContract, SectionDraft


class SectionGenerationError(ValueError):
    """Raised when a section contract cannot be satisfied by supplied facts."""


def generate_section_draft(
    contract: SectionContract,
    claims: Iterable[Claim],
    *,
    bibliography: Iterable[BibTeXEntry] = (),
    metric_results: Iterable[MetricResult] = (),
) -> SectionDraft:
    """Build a source-labelled Markdown draft without inventing facts or numbers."""

    if contract.section_id is None or contract.manuscript_id is None:
        raise SectionGenerationError("section contract must be persisted before drafting")
    claim_map = {claim.claim_id: claim for claim in claims if claim.claim_id is not None}
    missing_claims = [
        claim_id for claim_id in contract.required_claim_ids if claim_id not in claim_map
    ]
    if missing_claims:
        raise SectionGenerationError(
            "section contract is missing claims: " + ", ".join(missing_claims)
        )
    bibliography_map = {entry.citation_key: entry for entry in bibliography}
    missing_citations = [
        key for key in contract.required_citation_keys if key not in bibliography_map
    ]
    if missing_citations:
        raise SectionGenerationError(
            "section contract is missing citations: " + ", ".join(missing_citations)
        )
    metric_map = {metric.metric_result_id: metric for metric in metric_results}
    missing_metrics = [
        metric_id
        for metric_id in contract.required_metric_result_ids
        if metric_id not in metric_map
    ]
    if missing_metrics:
        raise SectionGenerationError(
            "section contract is missing metrics: " + ", ".join(missing_metrics)
        )
    unverified_metrics = [
        metric_id
        for metric_id in contract.required_metric_result_ids
        if metric_map[metric_id].verification_status != "verified"
        or not metric_map[metric_id].is_final
    ]
    if unverified_metrics:
        raise SectionGenerationError(
            "section drafts require verified final metrics: " + ", ".join(unverified_metrics)
        )
    lines = [
        f"## {contract.section.replace('_', ' ').title()}",
        "",
        f"**Purpose:** {contract.purpose}",
        "",
        "### Evidence-bound claims",
    ]
    for claim_id in contract.required_claim_ids:
        claim = claim_map[claim_id]
        status_note = " (insufficient evidence)" if claim.status == "insufficient" else ""
        lines.append(
            f"- {{\u007bclaim:{claim.claim_id}\u007d}} [{claim.status}{status_note}]: {claim.text}"
        )
    if not contract.required_claim_ids:
        lines.append("- No Claim is approved for this section yet.")
    if contract.required_citation_keys:
        lines.extend(
            [
                "",
                "### Sources",
                *[f"- [@{key}]" for key in contract.required_citation_keys],
            ]
        )
    if contract.required_metric_result_ids:
        lines.extend(
            [
                "",
                "### Verified metrics",
                *[
                    f"- {{\u007bmetric:{metric_id} value={metric_map[metric_id].value:.17g}\u007d}}"
                    for metric_id in contract.required_metric_result_ids
                ],
            ]
        )
    lines.extend(
        [
            "",
            "<!-- Generated from SectionContract; revise only after source checks. -->",
        ]
    )
    markdown = "\n".join(lines) + "\n"
    digest = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    return SectionDraft(
        section_id=contract.section_id,
        manuscript_id=contract.manuscript_id,
        markdown=markdown,
        claim_ids=list(contract.required_claim_ids),
        citation_keys=list(contract.required_citation_keys),
        metric_result_ids=list(contract.required_metric_result_ids),
        content_sha256=digest,
        generated_by="deterministic-template-v1",
    )
