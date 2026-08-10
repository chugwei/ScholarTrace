"""Contracts for controlled experiment execution.

The runner accepts an argv list, never a shell command string.  Paths are
relative to a per-run workspace so that a failed run cannot address a formal
artifact directory by accident.
"""

from datetime import datetime
from pathlib import PurePosixPath, PureWindowsPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scholartrace.schemas.research import NonBlankText

RunBackend = Literal["local", "docker"]
ControlledRunStatus = Literal[
    "queued",
    "running",
    "succeeded",
    "failed",
    "cancelled",
    "timed_out",
]
RunEventStream = Literal["stdout", "stderr", "system"]


def validate_relative_path(value: str, *, field_name: str = "path") -> str:
    """Validate a cross-platform path that must remain inside a run root."""

    normalized = value.replace("\\", "/")
    windows = PureWindowsPath(normalized)
    posix = PurePosixPath(normalized)
    if not normalized or "\x00" in normalized:
        raise ValueError(f"{field_name} must be a non-empty relative path")
    if windows.is_absolute() or windows.drive or posix.is_absolute():
        raise ValueError(f"{field_name} must be relative to the run workspace")
    if ".." in posix.parts:
        raise ValueError(f"{field_name} must not escape the run workspace")
    return normalized


class ResourceLimits(BaseModel):
    """Hard limits requested by a controlled run."""

    model_config = ConfigDict(extra="forbid")

    timeout_seconds: float = Field(gt=0, le=86_400)
    memory_mb: int = Field(gt=0, le=1_048_576)
    cpu_cores: float = Field(default=1, gt=0, le=128)
    cpu_seconds: float | None = Field(default=None, gt=0, le=86_400)
    max_log_bytes: int = Field(default=1_048_576, gt=0, le=100_000_000)
    max_output_bytes: int = Field(default=1_073_741_824, gt=0, le=10_737_418_240)


class ControlledRunSpec(BaseModel):
    """Immutable request for one execution against a frozen plan matrix row."""

    model_config = ConfigDict(extra="forbid")

    execution_id: NonBlankText
    project_id: NonBlankText
    plan_id: NonBlankText
    matrix_entry_id: NonBlankText
    command: list[NonBlankText] = Field(min_length=1)
    backend: RunBackend = "local"
    image: NonBlankText | None = None
    workspace_relpath: NonBlankText = "workspace"
    input_relpaths: list[NonBlankText] = Field(default_factory=list)
    output_relpath: NonBlankText = "outputs"
    environment: dict[str, NonBlankText] = Field(default_factory=dict)
    limits: ResourceLimits
    created_by: NonBlankText
    created_at: datetime

    @model_validator(mode="after")
    def validate_sandbox_contract(self) -> "ControlledRunSpec":
        validate_relative_path(self.workspace_relpath, field_name="workspace_relpath")
        validate_relative_path(self.output_relpath, field_name="output_relpath")
        if self.workspace_relpath == self.output_relpath:
            raise ValueError("output_relpath must be distinct from workspace_relpath")
        for path in self.input_relpaths:
            validate_relative_path(path, field_name="input_relpath")
        if self.backend == "docker" and self.image is None:
            raise ValueError("docker runs require an image")
        if self.backend == "local" and self.image is not None:
            raise ValueError("local runs must not specify a Docker image")
        if any("\x00" in token for token in self.command):
            raise ValueError("command arguments must not contain NUL bytes")
        for name, value in self.environment.items():
            if not name or "=" in name or "\x00" in name or "\x00" in value:
                raise ValueError("environment names and values must be NUL-free")
        return self


class ControlledRunRecord(BaseModel):
    """Persisted execution identity and lifecycle state."""

    model_config = ConfigDict(extra="forbid")

    execution_id: NonBlankText
    project_id: NonBlankText
    plan_id: NonBlankText
    matrix_entry_id: NonBlankText
    status: ControlledRunStatus
    backend: RunBackend
    command_sha256: str
    spec: ControlledRunSpec
    exit_code: int | None = None
    error: str | None = None
    log_relpath: str | None = None
    staging_relpath: str | None = None
    published_relpath: str | None = None
    event_count: int = Field(default=0, ge=0)
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ControlledRunEvent(BaseModel):
    """An ordered, bounded event emitted by a controlled run."""

    model_config = ConfigDict(extra="forbid")

    execution_id: NonBlankText
    sequence: int = Field(ge=0)
    stream: RunEventStream
    message: str = Field(max_length=100_000)
    created_at: datetime
