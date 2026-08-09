"""Validate all committed M0 project fixtures."""

from pathlib import Path

from scholartrace.fixtures import validate_fixture_directory


def main() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    fixture_directory = repository_root / "tests" / "fixtures" / "projects"
    fixtures = validate_fixture_directory(fixture_directory)
    project_ids = ", ".join(fixture.project_id for fixture in fixtures)
    print(f"validated {len(fixtures)} synthetic project fixtures: {project_ids}")


if __name__ == "__main__":
    main()
