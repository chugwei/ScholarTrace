import json
from pathlib import Path

from typer.testing import CliRunner

from scholartrace.cli import app

runner = CliRunner()


def write_question(path: Path, problem: str = "复杂果园背景中的荔枝病虫害小目标检测") -> None:
    path.write_text(
        json.dumps(
            {
                "problem": problem,
                "target_population_or_domain": "华南荔枝果园图像",
                "inputs": ["RGB 果园图像", "采集条件元数据"],
                "expected_outputs": ["病虫害类别", "目标边界框"],
                "constraints": ["类别体系待领域人员确认"],
                "success_criteria": ["独立测试集指标可复算"],
                "assumptions": ["正式数据已获得合法授权"],
                "unresolved_questions": ["小目标尺寸分层阈值如何确定"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def paths(tmp_path: Path) -> tuple[Path, Path]:
    return tmp_path / "domain.db", tmp_path / "checkpoints.db"


def database_options(domain_path: Path, checkpoint_path: Path) -> list[str]:
    return [
        "--database",
        str(domain_path),
        "--checkpoints",
        str(checkpoint_path),
    ]


def test_project_create_continue_and_show(tmp_path: Path) -> None:
    question_path = tmp_path / "question.json"
    domain_path, checkpoint_path = paths(tmp_path)
    write_question(question_path)
    common_options = database_options(domain_path, checkpoint_path)

    created = runner.invoke(
        app,
        [
            "project",
            "create",
            "lychee-pest-001",
            "--question-file",
            str(question_path),
            *common_options,
        ],
    )
    continued = runner.invoke(
        app,
        ["project", "continue", "lychee-pest-001", *common_options],
    )
    shown = runner.invoke(
        app,
        ["project", "show", "lychee-pest-001", "--database", str(domain_path)],
    )

    assert created.exit_code == 0, created.output
    assert continued.exit_code == 0, continued.output
    assert shown.exit_code == 0, shown.output

    created_payload = json.loads(created.stdout)
    continued_payload = json.loads(continued.stdout)
    shown_payload = json.loads(shown.stdout)
    assert created_payload["active_stage"] == "completed"
    assert continued_payload == created_payload
    assert shown_payload["project"]["project_id"] == "lychee-pest-001"
    assert shown_payload["project"]["thread_id"] == "lychee-pest-001"
    assert shown_payload["project"]["active_stage"] == "completed"
    assert len(shown_payload["research_questions"]) == 1
    assert (
        shown_payload["research_questions"][0]["research_question_id"]
        == created_payload["research_question_id"]
    )


def test_repeated_create_is_idempotent(tmp_path: Path) -> None:
    question_path = tmp_path / "question.json"
    domain_path, checkpoint_path = paths(tmp_path)
    write_question(question_path)
    arguments = [
        "project",
        "create",
        "lychee-pest-001",
        "--question-file",
        str(question_path),
        *database_options(domain_path, checkpoint_path),
    ]

    first = runner.invoke(app, arguments)
    replay = runner.invoke(app, arguments)
    shown = runner.invoke(
        app,
        ["project", "show", "lychee-pest-001", "--database", str(domain_path)],
    )

    assert first.exit_code == 0, first.output
    assert replay.exit_code == 0, replay.output
    assert json.loads(first.stdout) == json.loads(replay.stdout)
    assert len(json.loads(shown.stdout)["research_questions"]) == 1


def test_invalid_question_file_returns_usage_error_without_question(tmp_path: Path) -> None:
    question_path = tmp_path / "invalid.json"
    domain_path, checkpoint_path = paths(tmp_path)
    question_path.write_text('{"problem": "   "}', encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "project",
            "create",
            "invalid-question",
            "--question-file",
            str(question_path),
            *database_options(domain_path, checkpoint_path),
        ],
    )

    assert result.exit_code == 2
    assert "invalid research question" in result.stderr.lower()


def test_missing_project_and_checkpoint_return_clear_errors(tmp_path: Path) -> None:
    domain_path, checkpoint_path = paths(tmp_path)

    continued = runner.invoke(
        app,
        ["project", "continue", "missing", *database_options(domain_path, checkpoint_path)],
    )
    shown = runner.invoke(
        app,
        ["project", "show", "missing", "--database", str(domain_path)],
    )

    assert continued.exit_code == 1
    assert "was not found" in continued.stderr
    assert shown.exit_code == 1
    assert "was not found" in shown.stderr
