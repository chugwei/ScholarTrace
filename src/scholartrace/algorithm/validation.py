"""Evidence and completeness gates for algorithm-design contracts."""

from collections.abc import Collection

from scholartrace.schemas import (
    AlgorithmSpec,
    CandidateExperimentPlan,
    InnovationCandidate,
    InnovationValidationReport,
    PriorArtMap,
)
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


def validate_innovation_candidate(
    candidate: InnovationCandidate,
    prior_art_map: PriorArtMap,
    *,
    available_evidence_ids: Collection[str] | None = None,
) -> InnovationValidationReport:
    """Validate candidate references without deciding whether it is novel."""

    findings: list[InnovationFinding] = []
    if candidate.project_id != prior_art_map.project_id:
        findings.append(
            InnovationFinding(
                code="candidate.project_mismatch",
                severity="error",
                message="candidate and prior-art map must belong to the same project",
            )
        )
    if candidate.algorithm_id != prior_art_map.algorithm_id:
        findings.append(
            InnovationFinding(
                code="candidate.algorithm_mismatch",
                severity="error",
                message="candidate and prior-art map must reference the same algorithm",
            )
        )
    entry_ids = {entry.prior_art_entry_id for entry in prior_art_map.entries}
    missing_entries = sorted(set(candidate.prior_art_entry_ids) - entry_ids)
    if missing_entries:
        findings.append(
            InnovationFinding(
                code="candidate.missing_prior_art_entry",
                severity="error",
                message=(
                    f"candidate references unknown prior-art entries: {', '.join(missing_entries)}"
                ),
            )
        )
    map_evidence_ids = {
        evidence_id for entry in prior_art_map.entries for evidence_id in entry.evidence_card_ids
    }
    missing_map_evidence = sorted(set(candidate.prior_art_evidence_ids) - map_evidence_ids)
    if missing_map_evidence:
        findings.append(
            InnovationFinding(
                code="candidate.evidence_not_in_map",
                severity="error",
                message=(
                    "candidate evidence is not present in its prior-art map: "
                    f"{', '.join(missing_map_evidence)}"
                ),
            )
        )
    difference_entry_ids = {difference.prior_art_entry_id for difference in candidate.differences}
    missing_difference_entries = sorted(difference_entry_ids - entry_ids)
    if missing_difference_entries:
        findings.append(
            InnovationFinding(
                code="candidate.difference_entry_missing",
                severity="error",
                message=(
                    "method differences reference unknown prior-art entries: "
                    f"{', '.join(missing_difference_entries)}"
                ),
            )
        )
    if available_evidence_ids is not None:
        missing_evidence = sorted(
            set(candidate.prior_art_evidence_ids) - set(available_evidence_ids)
        )
        if missing_evidence:
            findings.append(
                InnovationFinding(
                    code="candidate.missing_evidence",
                    severity="error",
                    message=(
                        "candidate evidence cards are not present in this project: "
                        f"{', '.join(missing_evidence)}"
                    ),
                )
            )
    if candidate.novelty_status == "unverified":
        findings.append(
            InnovationFinding(
                code="candidate.novelty_unverified",
                severity="warning",
                message="novelty remains unverified until prior-art review and experiments",
            )
        )
    return InnovationValidationReport(
        passed=not any(item.severity == "error" for item in findings),
        findings=findings,
    )


def build_falsification_plan(candidate: InnovationCandidate) -> CandidateExperimentPlan:
    """Turn candidate fields into a reviewable proposal without running anything."""

    return CandidateExperimentPlan(
        candidate_id=candidate.candidate_id,
        hypothesis=(
            f"The proposed change should affect the stated mechanism: "
            f"{candidate.expected_mechanism}"
        ),
        falsification_experiment=candidate.falsification_experiment,
        required_baselines=candidate.required_baselines,
        required_ablations=candidate.required_ablations,
        evaluation_requirements=[
            "use the frozen dataset split and evaluation protocol",
            "report the candidate, every required baseline and every ablation",
            "record the code, data, configuration, seed and environment identifiers",
        ],
    )


def validate_candidate_for_experiment(
    candidate: InnovationCandidate,
    prior_art_map: PriorArtMap,
    *,
    algorithm_status: str,
    prior_art_status: str,
    available_evidence_ids: Collection[str] | None = None,
) -> InnovationValidationReport:
    """Gate entry to validation; this never upgrades a candidate to proven novelty."""

    report = validate_innovation_candidate(
        candidate,
        prior_art_map,
        available_evidence_ids=available_evidence_ids,
    )
    findings = list(report.findings)
    if algorithm_status != "approved":
        findings.append(
            InnovationFinding(
                code="candidate.algorithm_not_approved",
                severity="error",
                message="an algorithm specification must be approved before validation",
            )
        )
    if prior_art_status != "approved":
        findings.append(
            InnovationFinding(
                code="candidate.prior_art_not_approved",
                severity="error",
                message="a prior-art map must be approved before validation",
            )
        )
    if candidate.novelty_status == "not_novel":
        findings.append(
            InnovationFinding(
                code="candidate.not_novel",
                severity="error",
                message="a candidate marked not_novel cannot enter validation",
            )
        )
    if candidate.novelty_status == "conflicting":
        findings.append(
            InnovationFinding(
                code="candidate.conflicting_prior_art",
                severity="warning",
                message="conflicting prior-art evidence must remain visible to the reviewer",
            )
        )
    build_falsification_plan(candidate)
    return InnovationValidationReport(
        passed=not any(item.severity == "error" for item in findings),
        findings=findings,
    )
