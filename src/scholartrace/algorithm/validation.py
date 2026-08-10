"""Evidence and completeness gates for algorithm-design contracts."""

from collections.abc import Collection

from scholartrace.schemas import AlgorithmSpec, InnovationValidationReport, PriorArtMap
from scholartrace.schemas.algorithm import InnovationFinding


class AlgorithmValidationError(ValueError):
    """Raised when an algorithm design cannot pass a deterministic gate."""


def validate_algorithm_spec(
    spec: AlgorithmSpec,
    *,
    available_evidence_ids: Collection[str] | None = None,
) -> InnovationValidationReport:
    """Check traceability references without inferring scientific merit."""

    findings: list[InnovationFinding] = []
    if available_evidence_ids is not None:
        missing = sorted(set(spec.evidence_card_ids) - set(available_evidence_ids))
        if missing:
            findings.append(
                InnovationFinding(
                    code="algorithm.missing_evidence",
                    severity="error",
                    message=f"evidence cards are not present in this project: {', '.join(missing)}",
                )
            )
    return InnovationValidationReport(
        passed=not any(item.severity == "error" for item in findings), findings=findings
    )


def validate_prior_art_map(
    prior_art_map: PriorArtMap,
    *,
    available_evidence_ids: Collection[str] | None = None,
) -> InnovationValidationReport:
    """Require every prior-art row to carry resolvable evidence references."""

    findings: list[InnovationFinding] = []
    evidence_ids = {
        evidence_id for entry in prior_art_map.entries for evidence_id in entry.evidence_card_ids
    }
    if available_evidence_ids is not None:
        missing = sorted(evidence_ids - set(available_evidence_ids))
        if missing:
            findings.append(
                InnovationFinding(
                    code="prior_art.missing_evidence",
                    severity="error",
                    message=(
                        "prior-art evidence cards are not present in this project: "
                        f"{', '.join(missing)}"
                    ),
                )
            )
    if prior_art_map.unresolved_search_gaps:
        findings.append(
            InnovationFinding(
                code="prior_art.unresolved_search_gaps",
                severity="warning",
                message="the prior-art map has explicitly recorded unresolved search gaps",
            )
        )
    return InnovationValidationReport(
        passed=not any(item.severity == "error" for item in findings),
        findings=findings,
    )
