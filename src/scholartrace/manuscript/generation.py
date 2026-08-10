"""Deterministic section-draft generation from manuscript contracts."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

from scholartrace.schemas import BibTeXEntry, Claim, SectionContract, SectionDraft


class SectionGenerationError(ValueError):
    """Raised when a section contract cannot be satisfied by supplied facts."""


def generate_section_draft(
    contract: SectionContract,
    claims: Iterable[Claim],
    *,
    bibliography: Iterable[BibTeXEntry] = (),
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
        lines.append(f"- `{claim.claim_id}` [{claim.status}{status_note}]: {claim.text}")
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
        content_sha256=digest,
        generated_by="deterministic-template-v1",
    )
