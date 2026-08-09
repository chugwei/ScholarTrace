"""Shared validation for externally supplied project identifiers."""

import re

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def validate_identifier(value: str) -> str:
    """Reject empty, path-like, whitespace-padded, or oversized identifiers."""

    if not _IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError(
            "identifier must start with an ASCII letter or digit and contain only "
            "letters, digits, dots, underscores, or hyphens (maximum 128 characters)"
        )
    return value
