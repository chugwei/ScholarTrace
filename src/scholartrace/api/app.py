"""FastAPI resource API backed by the existing local repositories."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from scholartrace import __version__
from scholartrace.persistence.migrations import upgrade_database
from scholartrace.persistence.repository import (
    ProjectIdentityConflictError,
    ProjectNotFoundError,
    ProjectRepository,
)
from scholartrace.persistence.runner_repository import (
    ControlledRunConflictError,
    ControlledRunRepository,
    ControlledRunRepositoryError,
)
from scholartrace.schemas import (
    ArtifactResponse,
    ControlledRunRecord,
    ControlledRunSpec,
    ProjectCreateRequest,
    ProjectResponse,
)


def create_app(database_path: Path | None = None) -> FastAPI:
    """Create an isolated API application for a database path."""

    path = (database_path or Path(".scholartrace/domain.db")).expanduser()
    upgrade_database(path)
    projects = ProjectRepository(path)
    runs = ControlledRunRepository(path)
    app = FastAPI(title="研迹 ScholarTrace API", version=__version__)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.post("/api/projects", response_model=ProjectResponse, status_code=201)
    def create_project(request: ProjectCreateRequest) -> ProjectResponse:
        try:
            record = projects.create_project(
                request.project_id,
                request.thread_id,
                request.current_goal,
            )
        except ProjectIdentityConflictError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return ProjectResponse.model_validate(asdict(record))

    @app.get("/api/projects", response_model=list[ProjectResponse])
    def list_projects() -> list[ProjectResponse]:
        return [
            ProjectResponse.model_validate(asdict(record)) for record in projects.list_projects()
        ]

    @app.get("/api/projects/{project_id}", response_model=ProjectResponse)
    def get_project(project_id: str) -> ProjectResponse:
        try:
            record = projects.get_project(project_id)
        except ProjectNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return ProjectResponse.model_validate(asdict(record))

    @app.post(
        "/api/projects/{project_id}/runs", response_model=ControlledRunRecord, status_code=201
    )
    def create_run(project_id: str, request: ControlledRunSpec) -> ControlledRunRecord:
        if request.project_id != project_id:
            raise HTTPException(status_code=400, detail="request project_id does not match path")
        try:
            return runs.create_run(request)
        except ControlledRunConflictError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ControlledRunRepositoryError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get("/api/projects/{project_id}/runs", response_model=list[ControlledRunRecord])
    def list_runs(project_id: str) -> list[ControlledRunRecord]:
        try:
            return runs.list_runs(project_id)
        except ControlledRunRepositoryError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.get(
        "/api/projects/{project_id}/runs/{execution_id}",
        response_model=ControlledRunRecord,
    )
    def get_run(project_id: str, execution_id: str) -> ControlledRunRecord:
        try:
            return runs.get_run(project_id, execution_id)
        except ControlledRunRepositoryError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.get("/api/projects/{project_id}/artifacts", response_model=list[ArtifactResponse])
    def list_artifacts(project_id: str) -> list[ArtifactResponse]:
        try:
            records = runs.list_runs(project_id)
        except ControlledRunRepositoryError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return [_artifact_response(record) for record in records if _has_artifact(record)]

    @app.get(
        "/api/projects/{project_id}/artifacts/{execution_id}",
        response_model=ArtifactResponse,
    )
    def get_artifact(project_id: str, execution_id: str) -> ArtifactResponse:
        record = get_run(project_id, execution_id)
        if not _has_artifact(record):
            raise HTTPException(status_code=404, detail="run has no published or staging artifact")
        return _artifact_response(record)

    @app.get("/api/projects/{project_id}/runs/{execution_id}/events")
    def list_run_events(project_id: str, execution_id: str) -> list[dict[str, object]]:
        try:
            return [
                event.model_dump(mode="json")
                for event in runs.list_events(project_id, execution_id)
            ]
        except ControlledRunRepositoryError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.get("/api/projects/{project_id}/runs/{execution_id}/events/stream")
    def stream_run_events(project_id: str, execution_id: str) -> StreamingResponse:
        try:
            events = runs.list_events(project_id, execution_id)
        except ControlledRunRepositoryError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

        def event_stream() -> Iterator[str]:
            for event in events:
                payload = json.dumps(event.model_dump(mode="json"), ensure_ascii=False)
                yield f"id: {event.sequence}\nevent: {event.stream}\ndata: {payload}\n\n"
            yield ": keep-alive\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


def _has_artifact(record: ControlledRunRecord) -> bool:
    return any(
        path is not None
        for path in (record.log_relpath, record.staging_relpath, record.published_relpath)
    )


def _artifact_response(record: ControlledRunRecord) -> ArtifactResponse:
    return ArtifactResponse(
        execution_id=record.execution_id,
        project_id=record.project_id,
        status=record.status,
        log_relpath=record.log_relpath,
        staging_relpath=record.staging_relpath,
        published_relpath=record.published_relpath,
    )
