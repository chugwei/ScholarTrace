"""Command-line interface for the M1 project workflow."""

import json
import os
import sys
from pathlib import Path
from typing import Annotated, Any, NoReturn

import typer
from pydantic import ValidationError

from scholartrace.graphs.research_project import (
    CheckpointNotFoundError,
    open_research_project_graph,
)
from scholartrace.persistence.migrations import upgrade_database
from scholartrace.persistence.repository import (
    ProjectRecord,
    ProjectRepository,
    ProjectRepositoryError,
    ResearchQuestionRecord,
)
from scholartrace.schemas import ResearchQuestion
from scholartrace.states import ResearchProjectState, new_research_project_state


def _configure_windows_utf8() -> None:
    if os.name != "nt":
        return
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")


_configure_windows_utf8()

DEFAULT_DATABASE = Path(".scholartrace/scholartrace.db")
DEFAULT_CHECKPOINTS = Path(".scholartrace/checkpoints.db")

app = typer.Typer(help="研迹 ScholarTrace 科研项目工作台。", no_args_is_help=True)
project_app = typer.Typer(help="创建、继续和查看科研项目。", no_args_is_help=True)
app.add_typer(project_app, name="project")


@project_app.command("create")
def create_project(
    project_id: Annotated[str, typer.Argument(help="稳定的项目标识符。")],
    question_file: Annotated[
        Path,
        typer.Option("--question-file", help="UTF-8 ResearchQuestion JSON 文件。"),
    ],
    thread_id: Annotated[
        str | None,
        typer.Option("--thread-id", help="Checkpoint thread. 默认与 project_id 相同。"),
    ] = None,
    current_goal: Annotated[
        str,
        typer.Option("--current-goal", help="当前研究目标摘要。"),
    ] = "定义可检验的研究问题",
    database: Annotated[
        Path,
        typer.Option("--database", help="业务 SQLite 文件。"),
    ] = DEFAULT_DATABASE,
    checkpoints: Annotated[
        Path,
        typer.Option("--checkpoints", help="LangGraph checkpoint SQLite 文件。"),
    ] = DEFAULT_CHECKPOINTS,
) -> None:
    """创建项目并执行 M1 研究问题图。"""

    question = _load_question(question_file)
    try:
        state = new_research_project_state(
            project_id=project_id,
            thread_id=thread_id or project_id,
            current_goal=current_goal,
        )
        state["draft_research_question"] = question
        with open_research_project_graph(database, checkpoints) as workflow:
            result = workflow.invoke(state)
    except (ProjectRepositoryError, ValueError) as error:
        _fail(str(error))
    _write_json(_state_summary(result))


@project_app.command("continue")
def continue_project(
    project_id: Annotated[str, typer.Argument(help="要继续的项目标识符。")],
    database: Annotated[
        Path,
        typer.Option("--database", help="业务 SQLite 文件。"),
    ] = DEFAULT_DATABASE,
    checkpoints: Annotated[
        Path,
        typer.Option("--checkpoints", help="LangGraph checkpoint SQLite 文件。"),
    ] = DEFAULT_CHECKPOINTS,
) -> None:
    """从项目绑定的 thread checkpoint 继续执行。"""

    try:
        project = _get_project(database, project_id)
        with open_research_project_graph(database, checkpoints) as workflow:
            result = workflow.resume(project.thread_id)
    except (ProjectRepositoryError, CheckpointNotFoundError, ValueError) as error:
        _fail(str(error))
    _write_json(_state_summary(result))


@project_app.command("show")
def show_project(
    project_id: Annotated[str, typer.Argument(help="要查看的项目标识符。")],
    database: Annotated[
        Path,
        typer.Option("--database", help="业务 SQLite 文件。"),
    ] = DEFAULT_DATABASE,
) -> None:
    """只读展示项目及其研究问题版本。"""

    try:
        upgrade_database(database)
        repository = ProjectRepository(database)
        try:
            project = repository.get_project(project_id)
            questions = repository.list_research_questions(project_id)
        finally:
            repository.close()
    except (ProjectRepositoryError, ValueError) as error:
        _fail(str(error))
    _write_json(
        {
            "project": _project_payload(project),
            "research_questions": [_question_payload(item) for item in questions],
        }
    )


def _load_question(path: Path) -> ResearchQuestion:
    try:
        return ResearchQuestion.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValidationError, ValueError) as error:
        raise typer.BadParameter(
            f"invalid research question: {error}",
            param_hint="--question-file",
        ) from error


def _get_project(database: Path, project_id: str) -> ProjectRecord:
    upgrade_database(database)
    repository = ProjectRepository(database)
    try:
        return repository.get_project(project_id)
    finally:
        repository.close()


def _state_summary(state: ResearchProjectState) -> dict[str, Any]:
    return {
        "project_id": state["project_id"],
        "thread_id": state["thread_id"],
        "active_stage": state["active_stage"],
        "research_question_id": state["research_question_id"],
    }


def _project_payload(project: ProjectRecord) -> dict[str, Any]:
    return {
        "project_id": project.project_id,
        "thread_id": project.thread_id,
        "active_stage": project.active_stage,
        "current_goal": project.current_goal,
        "created_at": project.created_at.isoformat(timespec="microseconds") + "Z",
        "updated_at": project.updated_at.isoformat(timespec="microseconds") + "Z",
    }


def _question_payload(record: ResearchQuestionRecord) -> dict[str, Any]:
    return {
        "research_question_id": record.research_question_id,
        "version": record.version,
        "content_sha256": record.content_sha256,
        "status": record.status,
        "frozen_at": (
            record.frozen_at.isoformat(timespec="microseconds") + "Z"
            if record.frozen_at is not None
            else None
        ),
        "frozen_by": record.frozen_by,
        "parent_research_question_id": record.parent_research_question_id,
        "question": record.question.model_dump(mode="json"),
        "created_at": record.created_at.isoformat(timespec="microseconds") + "Z",
    }


def _write_json(payload: dict[str, Any]) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


def _fail(message: str) -> NoReturn:
    typer.echo(f"error: {message}", err=True)
    raise typer.Exit(code=1)
