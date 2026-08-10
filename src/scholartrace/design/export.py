"""Deterministic Markdown/YAML export for approved research designs."""

from __future__ import annotations

from pathlib import Path

import yaml

from scholartrace.identifiers import validate_identifier
from scholartrace.schemas import (
    DataCollectionProtocol,
    PipelineSpec,
    PipelineVersionComparison,
)


class DesignExportError(ValueError):
    """Raised when a design cannot be published as a formal export."""


def export_design_bundle(
    pipeline: PipelineSpec,
    protocol: DataCollectionProtocol,
    output_root: Path,
) -> dict[str, Path]:
    """Write approved pipeline/protocol Markdown and YAML files atomically enough for local use."""

    _require_approved(pipeline.status, "pipeline")
    _require_approved(protocol.status, "data-collection protocol")
    if pipeline.project_id != protocol.project_id:
        raise DesignExportError("pipeline and protocol must belong to the same project")
    project_id = validate_identifier(pipeline.project_id)
    root = output_root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    files = {
        "pipeline_markdown": root / f"{project_id}-pipeline-v{pipeline.version}.md",
        "pipeline_yaml": root / f"{project_id}-pipeline-v{pipeline.version}.yaml",
        "protocol_markdown": root / f"{project_id}-protocol-v{protocol.version}.md",
        "protocol_yaml": root / f"{project_id}-protocol-v{protocol.version}.yaml",
    }
    _write(files["pipeline_markdown"], pipeline_to_markdown(pipeline))
    _write(files["pipeline_yaml"], _to_yaml(pipeline.model_dump(mode="json")))
    _write(files["protocol_markdown"], protocol_to_markdown(protocol))
    _write(files["protocol_yaml"], _to_yaml(protocol.model_dump(mode="json")))
    return files


def pipeline_to_markdown(spec: PipelineSpec) -> str:
    _require_approved(spec.status, "pipeline")
    lines = [
        f"# {spec.title}",
        "",
        f"- Project: `{spec.project_id}`",
        f"- Pipeline ID: `{spec.pipeline_id}`",
        f"- Version: `{spec.version}`",
        f"- Status: `{spec.status}`",
        f"- Content SHA-256: `{spec.content_sha256 or 'missing'}`",
        f"- Approved by: `{spec.approved_by or 'missing'}`",
        "",
        "## Objective",
        "",
        spec.objective,
        "",
        "## Stages",
        "",
    ]
    for index, stage in enumerate(spec.stages, start=1):
        lines.extend(
            [
                f"### {index}. {stage.name} (`{stage.stage_id}`)",
                "",
                f"Purpose: {stage.purpose}",
                "",
                f"- Inputs: {', '.join(stage.inputs)}",
                f"- Outputs: {', '.join(stage.outputs)}",
                f"- Tools: {', '.join(stage.tools) if stage.tools else 'none listed'}",
                "",
            ]
        )
    lines.extend(["## Evaluation", "", spec.evaluation_protocol, ""])
    return "\n".join(lines)


def protocol_to_markdown(protocol: DataCollectionProtocol) -> str:
    _require_approved(protocol.status, "data-collection protocol")
    lines = [
        f"# {protocol.title}",
        "",
        f"- Project: `{protocol.project_id}`",
        f"- Protocol ID: `{protocol.protocol_id}`",
        f"- Version: `{protocol.version}`",
        f"- Status: `{protocol.status}`",
        f"- Content SHA-256: `{protocol.content_sha256 or 'missing'}`",
        f"- Approved by: `{protocol.approved_by or 'missing'}`",
        "",
        "## Target and sampling",
        "",
        f"- Target population: {protocol.target_population}",
        f"- Sampling strategy: {protocol.sampling_strategy}",
        f"- Split strategy: {protocol.split_strategy}",
        "",
        "## Capture fields",
        "",
    ]
    lines.extend(
        f"- `{field.field_name}` ({'required' if field.required else 'optional'}): "
        f"{field.description}"
        for field in protocol.capture_fields
    )
    lines.extend(
        [
            "",
            "## Leakage controls",
            "",
            *[f"- {control}" for control in protocol.leakage_controls],
            "",
            "## Annotation and privacy",
            "",
            protocol.annotation_policy,
            "",
            protocol.consent_and_privacy,
            "",
        ]
    )
    return "\n".join(lines)


def comparison_to_markdown(comparison: PipelineVersionComparison) -> str:
    lines = [
        f"# Pipeline comparison: v{comparison.from_version} → v{comparison.to_version}",
        "",
        f"- Project: `{comparison.project_id}`",
        f"- From: `{comparison.from_pipeline_id}`",
        f"- To: `{comparison.to_pipeline_id}`",
        "",
        "## Changed fields",
        "",
    ]
    if comparison.changed_fields:
        lines.extend(f"- `{field}`" for field in comparison.changed_fields)
    else:
        lines.append("- none")
    lines.extend(["", "## Added stages", ""])
    if comparison.added_stage_ids:
        lines.extend(f"- `{stage_id}`" for stage_id in comparison.added_stage_ids)
    else:
        lines.append("- none")
    lines.extend(["", "## Removed stages", ""])
    if comparison.removed_stage_ids:
        lines.extend(f"- `{stage_id}`" for stage_id in comparison.removed_stage_ids)
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _require_approved(status: str, label: str) -> None:
    if status != "approved":
        raise DesignExportError(f"only approved {label}s can be formally exported")


def _to_yaml(payload: dict[str, object]) -> str:
    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)


def _write(path: Path, content: str) -> None:
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.replace(path)
