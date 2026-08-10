"""Deterministic completeness ranking for innovation candidates."""

from collections.abc import Iterable

from scholartrace.schemas import InnovationCandidate, InnovationCandidateRanking


def rank_innovation_candidates(
    candidates: Iterable[InnovationCandidate],
) -> list[InnovationCandidateRanking]:
    """Rank candidate completeness; the score is not a novelty or quality claim."""

    ranked = [_rank_one(candidate) for candidate in candidates]
    return sorted(ranked, key=lambda item: (-item.score, item.candidate_id))


def _rank_one(candidate: InnovationCandidate) -> InnovationCandidateRanking:
    evidence_score = min(len(candidate.prior_art_evidence_ids), 3) / 3 * 0.25
    difference_score = min(len(candidate.differences), 3) / 3 * 0.20
    mechanism_score = 0.20 if candidate.expected_mechanism.strip() else 0.0
    falsification_score = 0.20 if candidate.falsification_experiment.strip() else 0.0
    baseline_score = min(len(candidate.required_baselines), 2) / 2 * 0.075
    ablation_score = min(len(candidate.required_ablations), 2) / 2 * 0.075
    score = round(
        evidence_score
        + difference_score
        + mechanism_score
        + falsification_score
        + baseline_score
        + ablation_score,
        6,
    )
    rationale = [
        f"prior-art evidence references: {len(candidate.prior_art_evidence_ids)}",
        f"explicit method differences: {len(candidate.differences)}",
        "expected mechanism is recorded",
        "falsification experiment is recorded",
        f"required baselines: {len(candidate.required_baselines)}",
        f"required ablations: {len(candidate.required_ablations)}",
        "score ranks completeness only; it does not establish novelty",
    ]
    return InnovationCandidateRanking(
        candidate_id=candidate.candidate_id,
        score=score,
        rationale=rationale,
    )
