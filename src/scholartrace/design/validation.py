"""Deterministic research-design quality, leakage, and version checks."""

from __future__ import annotations

from scholartrace.schemas import (
    DataCollectionProtocol,
    DesignFinding,
    DesignValidationReport,
    PipelineSpec,
    PipelineVersionComparison,
)

_LEAKAGE_TERMS = ("group", "session", "source", "subject", "duplicate", "leak")


class DesignValidationError(ValueError):
    """Raised when a design pair cannot pass the approval gate."""

    def __init__(self, report: DesignValidationReport) -> None:
        self.report = report
        errors = "; ".join(item.message for item in report.findings if item.severity == "error")
        super().__init__(errors or "design validation failed")


def validate_pipeline_spec(spec: PipelineSpec) -> DesignValidationReport:
    findings: list[DesignFinding] = []
    for index, stage in enumerate(spec.stages[1:], start=1):
        previous = spec.stages[index - 1]
        prior_outputs = {value.casefold() for value in previous.outputs}
        incoming = {value.casefold() for value in stage.inputs}
        if not prior_outputs.intersection(incoming):
            findings.append(
                DesignFinding(
                    code="pipeline.disconnected_stage",
                    severity="error",
                    message=(
                        f"stage {stage.stage_id!r} has no input connected to "
                        f"the previous stage {previous.stage_id!r}"
                    ),
                    path=f"stages[{index}].inputs",
                )
            )
    return DesignValidationReport(passed=not _has_errors(findings), findings=findings)


def validate_data_collection_protocol(
    protocol: DataCollectionProtocol,
) -> DesignValidationReport:
    findings: list[DesignFinding] = []
    split_text = protocol.split_strategy.casefold()
    controls_text = " ".join(protocol.leakage_controls).casefold()
    if not any(term in split_text for term in _LEAKAGE_TERMS):
        findings.append(
            DesignFinding(
                code="protocol.split_leakage_risk",
                severity="error",
                message="split_strategy must name a grouping or source boundary",
                path="split_strategy",
            )
        )
    if not any(term in controls_text for term in _LEAKAGE_TERMS):
        findings.append(
            DesignFinding(
                code="protocol.leakage_control_missing",
                severity="error",
                message="leakage_controls must address group, session, source or duplicates",
                path="leakage_controls",
            )
        )
    return DesignValidationReport(passed=not _has_errors(findings), findings=findings)


def validate_design_pair(
    pipeline: PipelineSpec,
    protocol: DataCollectionProtocol,
) -> DesignValidationReport:
    if pipeline.project_id != protocol.project_id:
        return DesignValidationReport(
            passed=False,
            findings=[
                DesignFinding(
                    code="design.project_mismatch",
                    severity="error",
                    message="pipeline and protocol must belong to the same project",
                    path="project_id",
                )
            ],
        )
    findings = [
        *validate_pipeline_spec(pipeline).findings,
        *validate_data_collection_protocol(protocol).findings,
    ]
    return DesignValidationReport(passed=not _has_errors(findings), findings=findings)


def compare_pipeline_versions(
    before: PipelineSpec,
    after: PipelineSpec,
) -> PipelineVersionComparison:
    if before.project_id != after.project_id:
        raise ValueError("pipeline versions must belong to the same project")
    if after.version <= before.version:
        raise ValueError("after version must be newer than before version")
    excluded = {
        "pipeline_id",
        "project_id",
        "version",
        "status",
        "content_sha256",
        "parent_pipeline_id",
        "created_by",
        "decision_reason",
        "approved_by",
        "approved_at",
        "created_at",
    }
    before_payload = before.model_dump(mode="json", exclude=excluded)
    after_payload = after.model_dump(mode="json", exclude=excluded)
    changed_fields = sorted(
        field
        for field in set(before_payload) | set(after_payload)
        if before_payload.get(field) != after_payload.get(field)
    )
    before_stages = {stage.stage_id for stage in before.stages}
    after_stages = {stage.stage_id for stage in after.stages}
    return PipelineVersionComparison(
        project_id=before.project_id,
        from_pipeline_id=before.pipeline_id,
        to_pipeline_id=after.pipeline_id,
        from_version=before.version,
        to_version=after.version,
        changed_fields=changed_fields,
        added_stage_ids=sorted(after_stages - before_stages),
        removed_stage_ids=sorted(before_stages - after_stages),
    )


def _has_errors(findings: list[DesignFinding]) -> bool:
    return any(item.severity == "error" for item in findings)
