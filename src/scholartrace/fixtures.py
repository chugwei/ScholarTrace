"""Deterministic contracts for M0 project fixtures.

Fixtures are synthetic project descriptions used only for installation and
schema regression tests. They are not research evidence or validation results.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class ProjectFixture(BaseModel):
    """A de-identified, non-evidentiary agriculture vision project fixture."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    project_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=1, max_length=120)
    domain: Literal["agriculture_vision"]
    task_type: Literal[
        "object_detection",
        "object_counting",
        "image_classification",
    ]
    research_intent: str = Field(min_length=20)
    inputs: tuple[str, ...] = Field(min_length=1)
    expected_outputs: tuple[str, ...] = Field(min_length=1)
    constraints: tuple[str, ...] = Field(min_length=1)
    success_criteria: tuple[str, ...] = Field(min_length=1)
    assumptions: tuple[str, ...]
    unresolved_questions: tuple[str, ...]
    data_classification: Literal["synthetic_deidentified_fixture"]
    evidence_status: Literal["fixture_only_not_research_evidence"]
    contains_private_data: Literal[False]
    real_world_validation: Literal[False]

    @model_validator(mode="after")
    def reject_machine_specific_paths(self) -> ProjectFixture:
        """Keep committed examples portable and free of local absolute paths."""

        values = (
            self.research_intent,
            *self.inputs,
            *self.expected_outputs,
            *self.constraints,
            *self.success_criteria,
            *self.assumptions,
            *self.unresolved_questions,
        )
        forbidden_markers = (":\\", "file://", "\\\\wsl", "/home/", "/Users/")
        if any(marker in value for value in values for marker in forbidden_markers):
            raise ValueError("fixture contains a machine-specific absolute path")
        return self


class FixtureValidationError(ValueError):
    """Raised when a fixture directory violates the M0 fixture contract."""


def load_project_fixture(path: Path) -> ProjectFixture:
    """Load and validate a UTF-8 JSON fixture."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return ProjectFixture.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise FixtureValidationError(f"invalid project fixture {path.name}: {exc}") from exc


def validate_fixture_directory(
    directory: Path, *, minimum_count: int = 3
) -> tuple[ProjectFixture, ...]:
    """Validate all JSON fixtures and enforce count and project ID uniqueness."""

    paths = sorted(directory.glob("*.json"))
    if len(paths) < minimum_count:
        raise FixtureValidationError(
            f"expected at least {minimum_count} project fixtures, found {len(paths)}"
        )

    fixtures = tuple(load_project_fixture(path) for path in paths)
    project_ids = [fixture.project_id for fixture in fixtures]
    if len(project_ids) != len(set(project_ids)):
        raise FixtureValidationError("project fixture IDs must be unique")
    return fixtures
