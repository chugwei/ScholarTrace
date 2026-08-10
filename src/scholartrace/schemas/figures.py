"""Versioned, provenance-bound figure specifications."""

import math
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scholartrace.schemas.research import NonBlankText
from scholartrace.schemas.runner import validate_relative_path

FigureKind = Literal["line", "bar", "scatter", "histogram", "confusion_matrix", "table"]
FigureFormat = Literal["png", "svg", "pdf"]
FigureStatus = Literal["draft", "approved", "rejected"]
FigureSourceKind = Literal["metric_results", "dataset", "manual"]
FigureCheckStatus = Literal["passed", "failed"]


class FigurePoint(BaseModel):
    """One numeric point that can be written to input-data.csv."""

    model_config = ConfigDict(extra="forbid")

    label: NonBlankText
    value: float
    metric_result_id: NonBlankText | None = None

    @model_validator(mode="after")
    def validate_finite(self) -> "FigurePoint":
        if not math.isfinite(self.value):
            raise ValueError("figure point value must be finite")
        return self


class FigureSpec(BaseModel):
    """A reproducible figure design before rendering."""

    model_config = ConfigDict(extra="forbid")

    figure_id: NonBlankText
    project_id: NonBlankText
    title: NonBlankText
    kind: FigureKind
    source_kind: FigureSourceKind = "metric_results"
    x_label: NonBlankText
    y_label: NonBlankText
    points: list[FigurePoint] = Field(min_length=1)
    metric_result_ids: list[NonBlankText] = Field(default_factory=list)
    data_version: NonBlankText
    data_relpath: NonBlankText = "input-data.csv"
    script_relpath: NonBlankText = "generate_figure.py"
    caption: NonBlankText
    output_formats: list[FigureFormat] = Field(default_factory=lambda: ["png", "svg", "pdf"])
    width_inches: float = Field(default=6.4, gt=0, le=40)
    height_inches: float = Field(default=4.8, gt=0, le=40)
    dpi: int = Field(default=150, ge=72, le=600)
    status: FigureStatus = "draft"
    content_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    created_by: NonBlankText
    created_at: datetime

    @model_validator(mode="after")
    def validate_spec(self) -> "FigureSpec":
        if len(self.output_formats) != len(set(self.output_formats)):
            raise ValueError("figure output formats must be unique")
        if self.source_kind == "metric_results" and not self.metric_result_ids:
            raise ValueError("metric-result figures require metric_result_ids")
        if any(point.metric_result_id for point in self.points) and not self.metric_result_ids:
            raise ValueError("point metric references require metric_result_ids")
        validate_relative_path(self.data_relpath, field_name="figure data path")
        validate_relative_path(self.script_relpath, field_name="figure script path")
        return self


class FigureArtifactBundle(BaseModel):
    """Files and hashes published together for one rendered figure."""

    model_config = ConfigDict(extra="forbid")

    figure_id: NonBlankText
    project_id: NonBlankText
    bundle_relpath: NonBlankText
    data_relpath: NonBlankText
    script_relpath: NonBlankText
    caption_relpath: NonBlankText
    provenance_relpath: NonBlankText
    output_relpaths: dict[FigureFormat, NonBlankText]
    data_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    script_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    metric_result_ids: list[NonBlankText] = Field(default_factory=list)
    created_at: datetime


class FigureSuggestion(BaseModel):
    """A deterministic chart recommendation grounded in available metrics."""

    model_config = ConfigDict(extra="forbid")

    kind: FigureKind
    priority: int = Field(ge=1)
    metric_names: list[NonBlankText] = Field(min_length=1)
    rationale: NonBlankText


class FigureValidationReport(BaseModel):
    """Numeric and file provenance checks for a rendered bundle."""

    model_config = ConfigDict(extra="forbid")

    figure_id: NonBlankText
    numeric_status: FigureCheckStatus
    provenance_status: FigureCheckStatus
    mismatches: list[NonBlankText] = Field(default_factory=list)
    checked_at: datetime
