"""Caption, suggestion and numeric/provenance validation tools."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from scholartrace.schemas import (
    FigureArtifactBundle,
    FigureSpec,
    FigureSuggestion,
    FigureValidationReport,
    MetricResult,
)


def recommend_figure_types(metrics: list[MetricResult]) -> list[FigureSuggestion]:
    """Return stable suggestions using only verified/final metric records."""

    verified = [
        metric for metric in metrics if metric.verification_status == "verified" and metric.is_final
    ]
    if not verified:
        return []
    names = sorted({metric.name for metric in verified})
    suggestions = [
        FigureSuggestion(
            kind="bar",
            priority=1,
            metric_names=names,
            rationale="compare verified final metric values across the supplied records",
        )
    ]
    if len(verified) > 1:
        suggestions.append(
            FigureSuggestion(
                kind="line",
                priority=2,
                metric_names=names,
                rationale="show the ordered verified final values without inventing a trend",
            )
        )
    return suggestions


def build_caption(spec: FigureSpec, metrics: list[MetricResult]) -> str:
    """Build a bounded caption that names provenance without claiming causality."""

    verified_ids = {
        metric.metric_result_id
        for metric in metrics
        if metric.verification_status == "verified" and metric.is_final
    }
    bound_ids = [metric_id for metric_id in spec.metric_result_ids if metric_id in verified_ids]
    if set(bound_ids) != set(spec.metric_result_ids):
        raise ValueError("caption generation requires all referenced metrics to be verified final")
    return (
        f"{spec.title}. Values are from verified final MetricResult records "
        f"({', '.join(bound_ids)}) on data version {spec.data_version}."
    )


def validate_bundle_numeric_consistency(
    spec: FigureSpec,
    bundle: FigureArtifactBundle,
    bundle_root: Path,
    metrics: list[MetricResult],
) -> FigureValidationReport:
    """Check CSV values, MetricResult values and provenance hashes."""

    mismatches: list[str] = []
    root = bundle_root.expanduser().resolve()
    data_path = root / spec.data_relpath
    script_path = root / spec.script_relpath
    provenance_path = root / "provenance.json"
    try:
        with data_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, csv.Error) as error:
        return FigureValidationReport(
            figure_id=spec.figure_id,
            numeric_status="failed",
            provenance_status="failed",
            mismatches=[f"bundle could not be read: {error}"],
            checked_at=_utc_now(),
        )
    if len(rows) != len(spec.points):
        mismatches.append("CSV point count does not match FigureSpec")
    metric_by_id = {metric.metric_result_id: metric for metric in metrics}
    for index, point in enumerate(spec.points):
        if index >= len(rows):
            break
        row = rows[index]
        try:
            actual_value = float(row["value"])
        except (KeyError, ValueError):
            mismatches.append(f"CSV row {index} has no finite numeric value")
            continue
        if row.get("label") != point.label or actual_value != point.value:
            mismatches.append(f"CSV row {index} differs from FigureSpec point")
        if point.metric_result_id:
            metric = metric_by_id.get(point.metric_result_id)
            if metric is None or metric.value != actual_value:
                mismatches.append(
                    f"CSV row {index} differs from MetricResult {point.metric_result_id}"
                )
    numeric_status = "passed" if not mismatches else "failed"
    expected_provenance = {
        "data_sha256": _sha256(data_path),
        "script_sha256": _sha256(script_path),
        "metric_result_ids": spec.metric_result_ids,
        "data_version": spec.data_version,
    }
    provenance_status = "passed"
    for key, value in expected_provenance.items():
        if provenance.get(key) != value:
            provenance_status = "failed"
            mismatches.append(f"provenance field {key} does not match bundle")
    return FigureValidationReport(
        figure_id=spec.figure_id,
        numeric_status=numeric_status,
        provenance_status=provenance_status,
        mismatches=mismatches,
        checked_at=_utc_now(),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> datetime:
    return datetime.now(UTC)
