"""Command-line interface for the M1 project workflow."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, NoReturn

import typer

if TYPE_CHECKING:
    from scholartrace.persistence.repository import ProjectRecord, ResearchQuestionRecord
    from scholartrace.schemas import ResearchQuestion
    from scholartrace.states import ResearchProjectState


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


@app.command("app")
def run_app(
    host: Annotated[str, typer.Option(help="监听地址。")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="首选端口; 被占用时自动顺延。")] = 8000,
    database: Annotated[
        Path,
        typer.Option("--database", help="业务 SQLite 文件。"),
    ] = DEFAULT_DATABASE,
    browser: Annotated[
        bool,
        typer.Option("--browser", help="用默认浏览器代替桌面窗口。"),
    ] = False,
) -> None:
    """一键启动应用模式: 本地服务 + 桌面窗口 (关闭窗口即退出)。"""

    from scholartrace.launcher import (
        BackgroundServer,
        LauncherError,
        build_app_url,
        build_loading_html,
        find_free_port,
        open_browser,
        open_desktop_window,
    )

    def _build_application() -> object:
        # Imported inside the bootstrap thread so GUI startup overlaps the
        # heavy api/sqlalchemy import chain instead of waiting for it.
        from scholartrace.api.app import create_app

        return create_app(database)

    try:
        chosen_port = find_free_port(port, host=host)
    except LauncherError as error:
        _fail(str(error))
    url = build_app_url(host, chosen_port)

    def _report_boot_error(message: str) -> None:
        typer.echo(f"error: {message}", err=True)

    startup = BackgroundServer(
        _build_application,
        host=host,
        port=chosen_port,
        on_error=_report_boot_error,
    )
    startup.start()
    typer.echo(f"研迹 ScholarTrace 应用模式已启动: {url}")
    typer.echo(f"数据库: {database.resolve()}")
    try:
        if browser:
            typer.echo("按 Ctrl+C 退出。")
            startup.wait_ready()
            open_browser(url)
            startup.wait_for_exit()
        else:
            typer.echo("关闭窗口即退出。")
            open_desktop_window(
                url,
                on_close=startup.stop,
                loading_html=build_loading_html(url),
            )
    except LauncherError as error:
        _fail(str(error))
    except KeyboardInterrupt:
        typer.echo("正在退出应用模式…")
        return
    finally:
        startup.stop()
    if startup.error is not None:
        _fail(f"应用服务启动失败: {startup.error}")


@app.command("web")
def run_web(
    host: Annotated[str, typer.Option(help="监听地址。")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="监听端口。")] = 8000,
    database: Annotated[
        Path,
        typer.Option("--database", help="业务 SQLite 文件。"),
    ] = DEFAULT_DATABASE,
    delivery_root: Annotated[
        Path | None,
        typer.Option("--delivery-root", help="可选的只读交付包根目录。"),
    ] = None,
    delivery_manifest: Annotated[
        Path | None,
        typer.Option("--delivery-manifest", help="可选的 Delivery Manifest JSON。"),
    ] = None,
) -> None:
    """启动本地 FastAPI 工作台。"""

    import uvicorn

    from scholartrace.api.app import create_app

    try:
        application = create_app(
            database,
            delivery_root=delivery_root,
            delivery_manifest_path=delivery_manifest,
        )
    except (OSError, ValueError) as error:
        _fail(str(error))
    uvicorn.run(application, host=host, port=port)


@app.command("infer")
def infer_delivery(
    manifest_file: Annotated[
        Path,
        typer.Option("--manifest", help="Delivery Manifest JSON 文件。"),
    ],
    delivery_root: Annotated[
        Path,
        typer.Option("--delivery-root", help="已构建交付包的根目录。"),
    ],
    input_relpath: Annotated[
        str,
        typer.Option("--input", help="Manifest 中登记的相对输入路径。"),
    ],
    request_id: Annotated[str, typer.Option(help="可追踪的推理请求标识。")] = "inference-cli",
) -> None:
    """Run a manifest-bound offline inference request."""

    from pydantic import ValidationError

    from scholartrace.inference import InferenceContractError, InferenceService
    from scholartrace.schemas import DeliveryManifest, InferenceRequest
    from scholartrace.schemas.runner import validate_relative_path

    try:
        manifest = DeliveryManifest.model_validate_json(manifest_file.read_text(encoding="utf-8"))
        validate_relative_path(input_relpath, field_name="inference input path")
        input_path = delivery_root / input_relpath
        payload = input_path.read_bytes()
        response = InferenceService(delivery_root, manifest).predict(
            InferenceRequest(
                request_id=request_id,
                input_relpath=input_relpath,
                input_sha256=hashlib.sha256(payload).hexdigest(),
            )
        )
    except (InferenceContractError, OSError, ValidationError, ValueError) as error:
        _fail(str(error))
    _write_json(response.model_dump(mode="json"))


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

    from scholartrace.graphs.research_project import open_research_project_graph
    from scholartrace.persistence.repository import ProjectRepositoryError
    from scholartrace.states import new_research_project_state

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

    from scholartrace.graphs.research_project import (
        CheckpointNotFoundError,
        open_research_project_graph,
    )
    from scholartrace.persistence.repository import ProjectRepositoryError

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

    from scholartrace.persistence.migrations import upgrade_database
    from scholartrace.persistence.repository import (
        ProjectRepository,
        ProjectRepositoryError,
    )

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
    from pydantic import ValidationError

    from scholartrace.schemas import ResearchQuestion

    try:
        return ResearchQuestion.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValidationError, ValueError) as error:
        raise typer.BadParameter(
            f"invalid research question: {error}",
            param_hint="--question-file",
        ) from error


def _get_project(database: Path, project_id: str) -> ProjectRecord:
    from scholartrace.persistence.migrations import upgrade_database
    from scholartrace.persistence.repository import ProjectRepository

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
