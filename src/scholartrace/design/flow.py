"""Deterministic flow-diagram rendering for approved or draft pipeline specs."""

from scholartrace.schemas import PipelineSpec


def pipeline_to_mermaid(spec: PipelineSpec) -> str:
    """Render ordered PipelineStage records as a small, auditable Mermaid graph."""

    lines = ["flowchart LR"]
    for index, stage in enumerate(spec.stages):
        label = _escape(f"{stage.name} ({stage.stage_id})")
        lines.append(f'    stage_{index}["{label}"]')
        if index:
            lines.append(f"    stage_{index - 1} --> stage_{index}")
    return "\n".join(lines)


def _escape(value: str) -> str:
    return value.replace('"', "'").replace("\n", " ")
