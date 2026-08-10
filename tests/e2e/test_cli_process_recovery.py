import json
import subprocess
import sys
from pathlib import Path

import pytest

from scholartrace.persistence.repository import (
    ProjectRepository,
    ResearchQuestionNotFoundError,
)

REPOSITORY_ROOT = Path(__file__).parents[2]
GOLDEN_QUESTION = REPOSITORY_ROOT / "examples/agriculture-vision-project/research-question.json"


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "scholartrace", *arguments],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def storage_options(domain_path: Path, checkpoint_path: Path) -> list[str]:
    return [
        "--database",
        str(domain_path),
        "--checkpoints",
        str(checkpoint_path),
    ]


@pytest.mark.parametrize(
    "project_id",
    [
        "lychee-recovery-001",
        "lychee-recovery-002",
        "lychee-recovery-003",
    ],
)
def test_independent_process_recovery_is_complete_and_idempotent(
    tmp_path: Path,
    project_id: str,
) -> None:
    domain_path = tmp_path / "domain.db"
    checkpoint_path = tmp_path / "checkpoints.db"
    options = storage_options(domain_path, checkpoint_path)

    created = run_cli(
        "project",
        "create",
        project_id,
        "--question-file",
        str(GOLDEN_QUESTION),
        *options,
    )
    continued = run_cli("project", "continue", project_id, *options)
    replayed = run_cli(
        "project",
        "create",
        project_id,
        "--question-file",
        str(GOLDEN_QUESTION),
        *options,
    )
    shown = run_cli("project", "show", project_id, "--database", str(domain_path))

    assert created.returncode == 0, created.stderr
    assert continued.returncode == 0, continued.stderr
    assert replayed.returncode == 0, replayed.stderr
    assert shown.returncode == 0, shown.stderr

    created_payload = json.loads(created.stdout)
    continued_payload = json.loads(continued.stdout)
    replayed_payload = json.loads(replayed.stdout)
    shown_payload = json.loads(shown.stdout)
    assert continued_payload == created_payload
    assert replayed_payload == created_payload
    assert shown_payload["project"]["active_stage"] == "completed"
    assert len(shown_payload["research_questions"]) == 1
    assert shown_payload["research_questions"][0]["question"]["problem"].startswith("复杂果园背景")


def test_independent_process_projects_do_not_leak(tmp_path: Path) -> None:
    domain_path = tmp_path / "domain.db"
    checkpoint_path = tmp_path / "checkpoints.db"
    options = storage_options(domain_path, checkpoint_path)
    project_ids = ["isolation-a", "isolation-b"]

    results = [
        run_cli(
            "project",
            "create",
            project_id,
            "--question-file",
            str(GOLDEN_QUESTION),
            *options,
        )
        for project_id in project_ids
    ]
    assert all(result.returncode == 0 for result in results)

    repository = ProjectRepository(domain_path)
    first = repository.list_research_questions(project_ids[0])
    second = repository.list_research_questions(project_ids[1])
    assert len(first) == len(second) == 1
    assert first[0].research_question_id != second[0].research_question_id
    with pytest.raises(ResearchQuestionNotFoundError):
        repository.get_research_question(project_ids[1], first[0].research_question_id)
    repository.close()

    first_checkpoint = run_cli("project", "continue", project_ids[0], *options)
    second_checkpoint = run_cli("project", "continue", project_ids[1], *options)
    assert json.loads(first_checkpoint.stdout)["project_id"] == project_ids[0]
    assert json.loads(second_checkpoint.stdout)["project_id"] == project_ids[1]
