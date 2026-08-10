"""Deterministic, evidence-bound failure analysis."""

from scholartrace.debugging.analysis import (
    capture_failure,
    classify_failure,
    collect_environment,
    rank_hypotheses,
    run_safe_diagnostics,
)
from scholartrace.debugging.repair import SafeRepairError, SafeRepairWorkspace

__all__ = [
    "SafeRepairError",
    "SafeRepairWorkspace",
    "capture_failure",
    "classify_failure",
    "collect_environment",
    "rank_hypotheses",
    "run_safe_diagnostics",
]
