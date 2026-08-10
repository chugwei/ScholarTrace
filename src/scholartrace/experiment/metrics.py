"""Small, dependency-free metrics used for independent result checks."""

import math
from collections.abc import Iterable


def recompute_metric(name: str, predictions: Iterable[float], targets: Iterable[float]) -> float:
    """Recompute a metric from explicit predictions and targets.

    This function does not read training logs or infer missing data. Callers must
    persist the input data version and evaluation script provenance separately.
    """

    predicted = list(predictions)
    expected = list(targets)
    if not predicted or len(predicted) != len(expected):
        raise ValueError("predictions and targets must be non-empty and have equal length")
    if not all(math.isfinite(float(value)) for value in [*predicted, *expected]):
        raise ValueError("predictions and targets must be finite")
    normalized = name.strip().lower()
    if normalized == "accuracy":
        return sum(
            float(left) == float(right) for left, right in zip(predicted, expected, strict=True)
        ) / len(predicted)
    errors = [float(left) - float(right) for left, right in zip(predicted, expected, strict=True)]
    if normalized == "mae":
        return sum(abs(error) for error in errors) / len(errors)
    if normalized == "rmse":
        return math.sqrt(sum(error * error for error in errors) / len(errors))
    raise ValueError(f"unsupported metric for independent recomputation: {name!r}")
