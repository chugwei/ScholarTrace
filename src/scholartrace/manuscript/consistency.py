"""Cross-section manuscript consistency and evidence-gap checks."""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Mapping

from scholartrace.manuscript.citations import validate_citations
from scholartrace.schemas import (
    BibTeXEntry,
    Claim,
    ManuscriptConsistencyReport,
    MetricResult,
)

_CLAIM_MARKER = re.compile(r"\{\{claim:([A-Za-z][A-Za-z0-9:._-]*)\}\}")
_METRIC_MARKER = re.compile(
    r"\{\{metric:([A-Za-z][A-Za-z0-9:._-]*)\s+value=([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\}\}"
)


def validate_manuscript_consistency(
    sections: Mapping[str, str],
    *,
    claims: Iterable[Claim],
    metrics: Iterable[MetricResult],
    bibliography: Iterable[BibTeXEntry],
) -> ManuscriptConsistencyReport:
    """Validate source markers and cross-section numbers without guessing prose."""

    claim_map = {claim.claim_id: claim for claim in claims if claim.claim_id is not None}
    metric_map = {metric.metric_result_id: metric for metric in metrics}
    bibliography_entries = list(bibliography)
    combined_markdown = "\n".join(sections.values())
    citation_report = validate_citations(combined_markdown, bibliography_entries)
    missing_evidence: list[str] = []
    unsupported_claim_ids: list[str] = []
    missing_claim_ids: list[str] = []
    unbound_metric_markers: list[str] = []
    numeric_mismatches: list[str] = []
    conclusion_new_claim_ids: list[str] = []
    section_claims: dict[str, set[str]] = {}
    section_metrics: dict[str, dict[str, float]] = {}

    for section_name, markdown in sections.items():
        claim_ids = set(_CLAIM_MARKER.findall(markdown))
        section_claims[section_name] = claim_ids
        for claim_id in claim_ids:
            claim = claim_map.get(claim_id)
            if claim is None:
                missing_claim_ids.append(f"{section_name}:{claim_id}")
            elif claim.status != "supported":
                unsupported_claim_ids.append(claim_id)
        values: dict[str, float] = {}
        for metric_id, raw_value in _METRIC_MARKER.findall(markdown):
            value = float(raw_value)
            metric = metric_map.get(metric_id)
            if metric is None:
                unbound_metric_markers.append(f"{section_name}:{metric_id}")
                continue
            if metric.verification_status != "verified" or not metric.is_final:
                unbound_metric_markers.append(f"{section_name}:{metric_id}:unverified")
                continue
            if not math.isclose(value, metric.value, rel_tol=1e-12, abs_tol=1e-12):
                numeric_mismatches.append(
                    f"{section_name}:{metric_id} rendered={value:g} expected={metric.value:g}"
                )
            values[metric_id] = value
        section_metrics[section_name] = values

    for claim_id, claim in claim_map.items():
        if claim.status == "insufficient":
            missing_evidence.append(f"{claim_id}:insufficient")
        elif claim.status == "supported" and not (
            claim.evidence_ids or claim.experiment_run_ids or claim.metric_result_ids
        ):
            missing_evidence.append(f"{claim_id}:no-evidence")
        for location in claim.manuscript_locations:
            if location in sections and claim_id not in section_claims[location]:
                missing_claim_ids.append(f"{location}:{claim_id}")

    conclusion_claims = section_claims.get("conclusion", set())
    comparison_claims = section_claims.get("results", set()) | section_claims.get("abstract", set())
    conclusion_new_claim_ids.extend(sorted(conclusion_claims - comparison_claims))

    all_metric_ids = set().union(*(values.keys() for values in section_metrics.values()))
    for metric_id in sorted(all_metric_ids):
        rendered_values = {
            section: values[metric_id]
            for section, values in section_metrics.items()
            if metric_id in values
        }
        if len({f"{value:.12g}" for value in rendered_values.values()}) > 1:
            numeric_mismatches.append(
                f"cross-section:{metric_id} "
                + ", ".join(f"{section}={value:g}" for section, value in rendered_values.items())
            )

    status = (
        "passed"
        if not any(
            (
                citation_report.status == "failed",
                missing_evidence,
                unsupported_claim_ids,
                missing_claim_ids,
                unbound_metric_markers,
                numeric_mismatches,
                conclusion_new_claim_ids,
            )
        )
        else "failed"
    )
    return ManuscriptConsistencyReport(
        status=status,
        citation_report=citation_report,
        checked_sections=list(sections),
        missing_evidence=sorted(set(missing_evidence)),
        unsupported_claim_ids=sorted(set(unsupported_claim_ids)),
        missing_claim_ids=sorted(set(missing_claim_ids)),
        unbound_metric_markers=sorted(set(unbound_metric_markers)),
        numeric_mismatches=sorted(set(numeric_mismatches)),
        conclusion_new_claim_ids=sorted(set(conclusion_new_claim_ids)),
    )
