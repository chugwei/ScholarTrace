import json
from pathlib import Path

import pytest

from scholartrace.fixtures import (
    FixtureValidationError,
    ProjectFixture,
    load_project_fixture,
    validate_fixture_directory,
)

FIXTURE_DIRECTORY = Path(__file__).parents[1] / "fixtures" / "projects"


def test_each_committed_fixture_is_synthetic_and_not_validated_in_the_field() -> None:
    fixtures = validate_fixture_directory(FIXTURE_DIRECTORY)

    assert len(fixtures) == 3
    assert all(fixture.contains_private_data is False for fixture in fixtures)
    assert all(fixture.real_world_validation is False for fixture in fixtures)
    assert all(
        fixture.evidence_status == "fixture_only_not_research_evidence" for fixture in fixtures
    )


def test_fixture_rejects_machine_specific_absolute_path() -> None:
    fixture = load_project_fixture(FIXTURE_DIRECTORY / "lychee-pest-detection.json")
    payload = fixture.model_dump(mode="json")
    payload["inputs"] = ["C:\\private\\dataset"]

    with pytest.raises(ValueError, match="machine-specific absolute path"):
        ProjectFixture.model_validate(payload)


def test_fixture_rejects_unknown_contract_field() -> None:
    fixture = load_project_fixture(FIXTURE_DIRECTORY / "lychee-pest-detection.json")
    payload = fixture.model_dump(mode="json")
    payload["unreviewed_claim"] = "This field must not silently enter the contract."

    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        ProjectFixture.model_validate(payload)


def test_loader_reports_malformed_json(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{not-json", encoding="utf-8")

    with pytest.raises(FixtureValidationError, match=r"invalid project fixture malformed\.json"):
        load_project_fixture(malformed)


def test_directory_rejects_duplicate_project_ids(tmp_path: Path) -> None:
    source = FIXTURE_DIRECTORY / "lychee-pest-detection.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    for name in ("one.json", "two.json", "three.json"):
        (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(FixtureValidationError, match="IDs must be unique"):
        validate_fixture_directory(tmp_path)


def test_directory_requires_three_fixtures(tmp_path: Path) -> None:
    with pytest.raises(FixtureValidationError, match="expected at least 3"):
        validate_fixture_directory(tmp_path)
