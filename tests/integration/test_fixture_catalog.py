from pathlib import Path

from scholartrace.fixtures import validate_fixture_directory


def test_fixture_catalog_covers_three_agriculture_vision_tasks() -> None:
    fixture_directory = Path(__file__).parents[1] / "fixtures" / "projects"

    fixtures = validate_fixture_directory(fixture_directory)

    assert {fixture.task_type for fixture in fixtures} == {
        "image_classification",
        "object_counting",
        "object_detection",
    }
