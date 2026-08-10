"""Read-only failure classification and deterministic hypothesis ranking."""

from __future__ import annotations

import platform
import sys
from datetime import UTC, datetime
from pathlib import Path

from scholartrace.persistence.debug_case_repository import DebugCaseRepository
from scholartrace.persistence.runner_repository import ControlledRunRepository
from scholartrace.schemas import (
    DebugCase,
    DiagnosticFinding,
    DiagnosticHypothesis,
    EvidenceRef,
    FailureCategory,
)

_CATEGORY_RULES: tuple[tuple[FailureCategory, tuple[str, ...], str], ...] = (
    (
        "resource",
        ("out of memory", "oom", "memoryerror", "disk full", "timed out", "timeout"),
        "the run may have exceeded a declared resource or time limit",
    ),
    (
        "data",
        ("file not found", "dataset", "label", "corrupt", "no such file"),
        "an input dataset or label artifact may be missing or unreadable",
    ),
    (
        "configuration",
        ("config", "yaml", "toml", "invalid value", "missing required"),
        "a configuration value may be missing or inconsistent with the frozen plan",
    ),
    (
        "environment",
        ("modulenotfounderror", "importerror", "version", "dll", "cuda"),
        "the runtime environment or dependency lock may not match the run contract",
    ),
    (
        "evaluation",
        ("metric", "shape mismatch", "assertionerror", "nms", "threshold"),
        "the evaluation implementation or evaluation parameters may be inconsistent",
    ),
    (
        "convergence",
        ("nan", "inf", "loss", "diverg", "gradient"),
        "the optimization process may have failed to converge under this configuration",
    ),
    (
        "access",
        ("permission denied", "access denied", "forbidden", "unauthorized"),
        "the run may lack required file, device, or service permissions",
    ),
    (
        "reproducibility",
        ("seed", "determin", "reproduc", "random"),
        "the run may not have reproduced the declared seed or environment",
    ),
    (
        "code",
        ("traceback", "typeerror", "valueerror", "keyerror", "attributeerror"),
        "the application code may have raised an exception",
    ),
)


def classify_failure(error: str, log_text: str = "") -> FailureCategory:
    """Choose a category from observed strings without claiming root cause."""

    haystack = f"{error}\n{log_text}".casefold()
    scores = {
        category: sum(1 for keyword in keywords if keyword in haystack)
        for category, keywords, _statement in _CATEGORY_RULES
    }
    best = max(scores, key=lambda category: (scores[category], -_category_order(category)))
    return best if scores[best] else "unknown"


def rank_hypotheses(error: str, log_text: str = "") -> list[DiagnosticHypothesis]:
    """Return stable hypotheses ordered by keyword evidence and rule order."""

    haystack = f"{error}\n{log_text}".casefold()
    scored: list[tuple[int, int, FailureCategory, str, list[str]]] = []
    for index, (category, keywords, statement) in enumerate(_CATEGORY_RULES):
        matches = [keyword for keyword in keywords if keyword in haystack]
        if matches:
            scored.append((-len(matches), index, category, statement, matches))
    if not scored:
        return [
            DiagnosticHypothesis(
                hypothesis_id="hypothesis-unknown",
                category="unknown",
                statement="available failure evidence is insufficient to rank a specific category",
                priority=1,
            )
        ]
    scored.sort()
    hypotheses: list[DiagnosticHypothesis] = []
    for priority, (_negative_score, _index, category, statement, matches) in enumerate(
        scored, start=1
    ):
        hypotheses.append(
            DiagnosticHypothesis(
                hypothesis_id=f"hypothesis-{priority:02d}-{category}",
                category=category,
                statement=statement,
                priority=priority,
                evidence=[
                    EvidenceRef(source="failure-text", detail=f"matched keyword: {match}")
                    for match in matches
                ],
            )
        )
    return hypotheses


def collect_environment() -> dict[str, str]:
    """Collect non-secret runtime facts used to compare expected environments."""

    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "implementation": sys.implementation.name,
    }


def capture_failure(
    run_repository: ControlledRunRepository,
    case_repository: DebugCaseRepository,
    *,
    project_id: str,
    execution_id: str,
    case_id: str,
    expected_behavior: str,
) -> DebugCase:
    """Capture a failed Run and persist only observed evidence."""

    record = run_repository.get_run(project_id, execution_id)
    if record.status not in {"failed", "cancelled", "timed_out"}:
        raise ValueError("DebugCase capture requires a failed, cancelled, or timed-out run")
    events = run_repository.list_events(project_id, execution_id)
    log_text = "\n".join(event.message for event in events)
    observed_error = record.error or f"run ended with status {record.status}"
    now = datetime.now(UTC)
    case = DebugCase(
        case_id=case_id,
        project_id=project_id,
        execution_id=execution_id,
        category=classify_failure(observed_error, log_text),
        observed_error=observed_error,
        expected_behavior=expected_behavior,
        actual_behavior=f"status={record.status}; exit_code={record.exit_code}",
        staging_relpath=record.staging_relpath,
        log_relpath=record.log_relpath,
        environment=collect_environment(),
        created_at=now,
        updated_at=now,
    )
    return case_repository.save_case(case)


def diagnose_case(
    run_repository: ControlledRunRepository,
    case_repository: DebugCaseRepository,
    *,
    project_id: str,
    case_id: str,
    staging_root: Path,
) -> DebugCase:
    """Rank hypotheses and run read-only staging checks."""

    case = case_repository.get_case(project_id, case_id)
    events = run_repository.list_events(project_id, case.execution_id)
    log_text = "\n".join(event.message for event in events)
    hypotheses = rank_hypotheses(case.observed_error, log_text)
    findings = run_safe_diagnostics(case, staging_root)
    return case_repository.record_diagnosis(
        project_id,
        case_id,
        hypotheses=hypotheses,
        findings=findings,
    )


def run_safe_diagnostics(case: DebugCase, staging_root: Path) -> list[DiagnosticFinding]:
    """Check only paths and recorded evidence; never execute or modify inputs."""

    findings: list[DiagnosticFinding] = []
    if case.staging_relpath is None:
        findings.append(
            DiagnosticFinding(
                finding_id="finding-staging-path",
                status="unknown",
                check="staging path recorded",
                detail="the failed run did not persist a staging path",
            )
        )
        return findings
    staging = (staging_root / case.staging_relpath).resolve()
    try:
        staging.relative_to(staging_root.resolve())
    except ValueError:
        return [
            DiagnosticFinding(
                finding_id="finding-staging-escape",
                status="fail",
                check="staging path containment",
                detail="recorded staging path escapes the configured staging root",
            )
        ]
    findings.append(
        DiagnosticFinding(
            finding_id="finding-staging-exists",
            status="pass" if staging.is_dir() else "fail",
            check="staging directory exists",
            detail=f"staging directory: {staging.as_posix()}",
            evidence=[EvidenceRef(source="run-manifest", detail=case.staging_relpath)],
        )
    )
    if case.log_relpath is not None:
        log = (staging_root / case.log_relpath).resolve()
        try:
            log.relative_to(staging_root.resolve())
        except ValueError:
            findings.append(
                DiagnosticFinding(
                    finding_id="finding-log-escape",
                    status="fail",
                    check="log path containment",
                    detail="recorded log path escapes the configured staging root",
                )
            )
        else:
            findings.append(
                DiagnosticFinding(
                    finding_id="finding-log-exists",
                    status="pass" if log.is_file() else "unknown",
                    check="run log exists",
                    detail=f"log path: {log.as_posix()}",
                    evidence=[EvidenceRef(source="run-manifest", detail=case.log_relpath)],
                )
            )
    return findings


def _category_order(category: FailureCategory) -> int:
    for index, (candidate, _keywords, _statement) in enumerate(_CATEGORY_RULES):
        if candidate == category:
            return index
    return len(_CATEGORY_RULES)
