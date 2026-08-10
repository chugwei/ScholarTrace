"""Deterministic command validation and Docker sandbox construction."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from scholartrace.schemas.runner import ControlledRunSpec, validate_relative_path


class UnsafeCommandError(ValueError):
    """Raised when an execution request violates the command policy."""


_SHELL_MARKERS = re.compile(r"[;&|<>`$\r\n]")
_EXECUTABLE_ALIASES = {"python": "python", "python3": "python", "pytest": "pytest", "uv": "uv"}


@dataclass(frozen=True)
class CommandPolicy:
    """Allow a small, explicit executable set and reject shell semantics."""

    allowed_executables: frozenset[str] = field(
        default_factory=lambda: frozenset(_EXECUTABLE_ALIASES)
    )
    allowed_python_modules: frozenset[str] = field(
        default_factory=lambda: frozenset({"pytest", "scholartrace"})
    )

    def validate(self, command: list[str]) -> list[str]:
        if not command:
            raise UnsafeCommandError("command must not be empty")
        if any(not token or _SHELL_MARKERS.search(token) for token in command):
            raise UnsafeCommandError("command contains shell metacharacters")
        executable = Path(command[0]).name
        if Path(command[0]).name != command[0] or executable not in self.allowed_executables:
            raise UnsafeCommandError("executable must be an explicitly allowed name")
        if executable in {"python", "python3"}:
            self._validate_python_arguments(command[1:])
        return [str(token) for token in command]

    def validate_spec(self, spec: ControlledRunSpec) -> ControlledRunSpec:
        self.validate(spec.command)
        if (
            spec.backend == "docker"
            and spec.image is not None
            and (_SHELL_MARKERS.search(spec.image) or "@" in spec.image)
        ):
            raise UnsafeCommandError("Docker image contains unsafe characters")
        return spec

    def _validate_python_arguments(self, arguments: list[str]) -> None:
        if "-c" in arguments or "--command" in arguments:
            raise UnsafeCommandError("inline Python execution is disabled")
        for index, argument in enumerate(arguments):
            if argument in {"-m", "--module"}:
                try:
                    module = arguments[index + 1]
                except IndexError as error:
                    raise UnsafeCommandError("python module argument is missing") from error
                if module not in self.allowed_python_modules:
                    raise UnsafeCommandError("python module is not allowlisted")


@dataclass(frozen=True)
class DockerCommandBuilder:
    """Build an argv-only Docker command with read-only inputs."""

    docker_executable: str = "docker"

    def build(
        self,
        spec: ControlledRunSpec,
        *,
        workspace: Path,
        outputs: Path,
        policy: CommandPolicy | None = None,
    ) -> list[str]:
        if spec.backend != "docker" or spec.image is None:
            raise ValueError("DockerCommandBuilder requires a docker run spec")
        (policy or CommandPolicy()).validate_spec(spec)
        workspace = workspace.expanduser().resolve()
        outputs = outputs.expanduser().resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        outputs.mkdir(parents=True, exist_ok=True)
        validate_relative_path(spec.workspace_relpath, field_name="workspace_relpath")
        return [
            self.docker_executable,
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--cpus",
            str(spec.limits.cpu_cores),
            "--memory",
            f"{spec.limits.memory_mb}m",
            "--pids-limit",
            "256",
            "-v",
            f"{workspace}:/workspace:ro",
            "-v",
            f"{outputs}:/workspace/{spec.output_relpath}:rw",
            "-w",
            "/workspace",
            spec.image,
            *spec.command,
        ]
