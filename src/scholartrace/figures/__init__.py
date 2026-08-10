"""Reproducible figure rendering primitives."""

from scholartrace.figures.render import FigureRenderer, FigureRenderError
from scholartrace.figures.validation import (
    build_caption,
    recommend_figure_types,
    validate_bundle_numeric_consistency,
)

__all__ = [
    "FigureRenderError",
    "FigureRenderer",
    "build_caption",
    "recommend_figure_types",
    "validate_bundle_numeric_consistency",
]
