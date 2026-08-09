"""Run the deterministic local and CI quality gate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> None:
    """Run one check from the repository root and fail without masking output."""

    print(f"+ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=REPOSITORY_ROOT, check=True)


def main() -> None:
    python = sys.executable
    source_paths = ["src", "tests", "scripts"]
    run([python, "-m", "ruff", "format", "--check", *source_paths])
    run([python, "-m", "ruff", "check", *source_paths])
    run([python, "-m", "pytest"])
    run([python, "scripts/validate_fixtures.py"])
    print("ScholarTrace M0 quality gate passed.")


if __name__ == "__main__":
    main()
