"""FastAPI resource API backed by the existing local repositories."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import AsyncIterator
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from scholartrace import __version__
from scholartrace.inference import InferenceContractError, InferenceService
from scholartrace.llm import (
    LLMOutputValidationError,
    LLMProviderError,
    StructuredLLMProvider,
    load_llm_provider_from_env,
    propose_research_question,
)
from scholartrace.manuscript import SectionGenerationError, generate_section_draft
from scholartrace.persistence.evidence_repository import EvidenceRepository
from scholartrace.persistence.figure_repository import FigureRepository
from scholartrace.persistence.literature_repository import (
    DocumentNotFoundError,
    LiteratureRepository,
    LiteratureRepositoryError,
    ProjectDocumentConflictError,
)
from scholartrace.persistence.manuscript_repository import (
    ManuscriptDecisionConflictError,
    ManuscriptNotFoundError,
    ManuscriptRepository,
)
from scholartrace.persistence.migrations import upgrade_database
from scholartrace.persistence.repository import (
    ProjectIdentityConflictError,
    ProjectNotFoundError,
    ProjectRepository,
    ResearchQuestionConcurrentUpdateError,
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
    DeliveryManifest,
    InferenceRequest,
    InferenceResponse,
    LLMStatusResponse,
    Manuscript,
    ManuscriptCreateRequest,
    ManuscriptDraftResponse,
    ManuscriptReviewRequest,
    ProjectCreateRequest,
    ProjectDocument,
    ProjectDocumentReviewRequest,
    ProjectResponse,
    ResearchQuestion,
    ResearchQuestionCandidateRequest,
    ResearchQuestionCandidateResponse,
    SectionContract,
)


def create_app(
    database_path: Path | None = None,
    *,
    delivery_root: Path | None = None,
    delivery_manifest_path: Path | None = None,
    llm_provider: StructuredLLMProvider | None = None,
) -> FastAPI:
    """Create an isolated API application for a database path."""

    path = (database_path or Path(".scholartrace/domain.db")).expanduser()
    upgrade_database(path)
    projects = ProjectRepository(path)
    runs = ControlledRunRepository(path)
    literature = LiteratureRepository(path)
    evidence = EvidenceRepository(path)
    figures = FigureRepository(path)
    manuscripts = ManuscriptRepository(path)
    configured_llm = llm_provider or load_llm_provider_from_env()
    inference_service: InferenceService | None = None
    if delivery_root is not None or delivery_manifest_path is not None:
        if delivery_root is None or delivery_manifest_path is None:
            raise ValueError("delivery_root and delivery_manifest_path must be supplied together")
        manifest = DeliveryManifest.model_validate_json(
            delivery_manifest_path.read_text(encoding="utf-8")
        )
        inference_service = InferenceService(delivery_root, manifest)
    app = FastAPI(title="研迹 ScholarTrace API", version=__version__)
    app.mount(
        "/static",
        StaticFiles(directory=Path(__file__).resolve().parents[1] / "static"),
        name="static",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/api/llm/status", response_model=LLMStatusResponse)
    def llm_status() -> LLMStatusResponse:
        if configured_llm is None:
            return LLMStatusResponse(enabled=False)
        return LLMStatusResponse(
            enabled=True,
            provider=configured_llm.name,
            model=configured_llm.model,
        )

    @app.post("/api/inference", response_model=InferenceResponse)
    def run_inference(request: InferenceRequest) -> InferenceResponse:
        if inference_service is None:
            raise HTTPException(
                status_code=503,
                detail="inference service is unavailable; configure a delivery manifest",
            )
        try:
            return inference_service.predict(request)
        except (InferenceContractError, OSError, ValueError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

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
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
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
    def stream_run_events(
        request: Request,
        project_id: str,
        execution_id: str,
        after_sequence: int = Query(default=-1, ge=-1),
        last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
        live: bool = Query(default=False),
    ) -> StreamingResponse:
        try:
            runs.list_events(project_id, execution_id)
        except ControlledRunRepositoryError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        offset = after_sequence
        if last_event_id is not None:
            try:
                offset = max(offset, int(last_event_id))
            except ValueError as error:
                raise HTTPException(
                    status_code=400, detail="Last-Event-ID must be an integer"
                ) from error

        def _serialize(event: object) -> str:
            payload = json.dumps(event.model_dump(mode="json"), ensure_ascii=False)
            return f"id: {event.sequence}\nevent: {event.stream}\ndata: {payload}\n\n"

        async def event_stream() -> AsyncIterator[str]:
            yield "retry: 3000\n\n"
            cursor = offset
            while True:
                current = runs.list_events(project_id, execution_id)
                for event in current:
                    if event.sequence > cursor:
                        yield _serialize(event)
                        cursor = event.sequence
                yield ": keep-alive\n\n"
                if not live or await request.is_disconnected():
                    return
                await asyncio.sleep(1)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post("/api/projects/{project_id}/research-questions", status_code=201)
    def save_research_question(project_id: str, question: ResearchQuestion) -> dict[str, object]:
        try:
            record = projects.save_research_question(
                project_id,
                question,
                active_stage="question_defined",
            )
        except ResearchQuestionConcurrentUpdateError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except (ProjectNotFoundError, ValueError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return _question_payload(record)

    @app.post(
        "/api/projects/{project_id}/research-question-candidates",
        response_model=ResearchQuestionCandidateResponse,
    )
    def propose_research_question_candidate(
        project_id: str,
        request: ResearchQuestionCandidateRequest,
    ) -> ResearchQuestionCandidateResponse:
        if configured_llm is None:
            raise HTTPException(status_code=503, detail="LLM provider is not configured")
        try:
            projects.get_project(project_id)
            candidate = propose_research_question(
                configured_llm,
                problem=request.problem,
                context=request.context,
            )
        except ProjectNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except LLMOutputValidationError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except LLMProviderError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
        return ResearchQuestionCandidateResponse(
            candidate=candidate,
            provider=configured_llm.name,
            model=configured_llm.model,
            warnings=[
                "LLM output is an unverified candidate and is not saved automatically.",
                "Review every field before saving; no citation, metric, or approval is implied.",
            ],
        )

    @app.get("/api/projects/{project_id}/research-questions")
    def list_research_questions(project_id: str) -> list[dict[str, object]]:
        try:
            records = projects.list_research_questions(project_id)
        except (ProjectNotFoundError, ValueError) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return [_question_payload(record) for record in records]

    @app.get("/api/projects/{project_id}/documents")
    def list_documents(project_id: str) -> list[dict[str, object]]:
        try:
            documents = literature.list_approved_documents(project_id)
        except (RuntimeError, ValueError) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return [document.model_dump(mode="json") for document in documents]

    @app.get("/api/projects/{project_id}/project-documents")
    def list_project_documents(project_id: str) -> list[dict[str, object]]:
        """List every project literature decision with its catalog metadata."""

        try:
            links = literature.list_project_documents(project_id)
            return [
                {
                    "link": link.model_dump(mode="json"),
                    "document": literature.get_document(link.document_id).model_dump(mode="json"),
                }
                for link in links
            ]
        except (LiteratureRepositoryError, ValueError) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.post(
        "/api/projects/{project_id}/project-documents/{document_id}/review",
        response_model=ProjectDocument,
    )
    def review_project_document(
        project_id: str,
        document_id: str,
        request: ProjectDocumentReviewRequest,
    ) -> ProjectDocument:
        try:
            return literature.review_project_document(
                project_id,
                document_id,
                status=request.status,
                actor_id=request.actor_id,
                reason=request.reason,
                relevance_score=request.relevance_score,
            )
        except DocumentNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ProjectDocumentConflictError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except (LiteratureRepositoryError, ValueError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get("/api/projects/{project_id}/evidence")
    def list_evidence(project_id: str) -> list[dict[str, object]]:
        try:
            cards = evidence.list_project_cards(project_id)
        except (RuntimeError, ValueError) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return [card.model_dump(mode="json") for card in cards]

    @app.get("/api/projects/{project_id}/figures")
    def list_figures(project_id: str) -> list[dict[str, object]]:
        try:
            specs = figures.list_specs(project_id)
        except (RuntimeError, ValueError) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return [spec.model_dump(mode="json") for spec in specs]

    @app.post("/api/projects/{project_id}/manuscripts", response_model=Manuscript, status_code=201)
    def create_manuscript(
        project_id: str,
        request: ManuscriptCreateRequest,
    ) -> Manuscript:
        try:
            projects.get_project(project_id)
            existing = manuscripts.list_manuscripts(project_id)
            version = existing[-1].version + 1 if existing else 1
            parent_id = existing[-1].manuscript_id if existing else None
            manuscript_id = (
                "ms-"
                + hashlib.sha256(f"{project_id}:{request.title}:{version}".encode()).hexdigest()[
                    :24
                ]
            )
            saved = manuscripts.save_manuscript(
                Manuscript(
                    manuscript_id=manuscript_id,
                    project_id=project_id,
                    title=request.title,
                    target_template=request.target_template,
                    version=version,
                    parent_manuscript_id=parent_id,
                    created_by="workbench",
                    created_at=datetime.now(UTC),
                )
            )
            for section, purpose, allow_new_claims in (
                ("abstract", "Summarize only supported research facts.", True),
                ("methods", "Describe the frozen research method.", True),
                ("results", "Report verified metrics and figures.", True),
                ("conclusion", "Summarize claims already present in results.", False),
            ):
                manuscripts.save_section_contract(
                    SectionContract(
                        section_id=f"{manuscript_id}-{section}",
                        manuscript_id=manuscript_id,
                        section=section,
                        purpose=purpose,
                        allow_new_claims=allow_new_claims,
                        created_by="workbench",
                        created_at=datetime.now(UTC),
                    )
                )
        except (RuntimeError, ValueError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return saved

    @app.get("/api/projects/{project_id}/manuscripts", response_model=list[Manuscript])
    def list_manuscripts(project_id: str) -> list[Manuscript]:
        try:
            return manuscripts.list_manuscripts(project_id)
        except (RuntimeError, ValueError) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.get(
        "/api/projects/{project_id}/manuscripts/{manuscript_id}/draft",
        response_model=ManuscriptDraftResponse,
    )
    def get_manuscript_draft(project_id: str, manuscript_id: str) -> ManuscriptDraftResponse:
        try:
            manuscript = manuscripts.get_manuscript(project_id, manuscript_id)
            contracts = manuscripts.list_section_contracts(manuscript_id)
            claims = manuscripts.list_claims(project_id)
        except (RuntimeError, ValueError) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        drafts = []
        errors: list[str] = []
        for contract in contracts:
            try:
                drafts.append(generate_section_draft(contract, claims))
            except SectionGenerationError as error:
                errors.append(f"{contract.section}: {error}")
        return ManuscriptDraftResponse(
            manuscript_id=manuscript.manuscript_id, sections=drafts, errors=errors
        )

    @app.post(
        "/api/projects/{project_id}/manuscripts/{manuscript_id}/review",
        response_model=Manuscript,
    )
    def submit_manuscript_for_review(
        project_id: str,
        manuscript_id: str,
        request: ManuscriptReviewRequest,
    ) -> Manuscript:
        try:
            return manuscripts.submit_for_review(
                project_id,
                manuscript_id,
                actor_id=request.actor_id,
                reason=request.reason,
            )
        except ManuscriptNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except (ManuscriptDecisionConflictError, ValueError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get("/", response_class=HTMLResponse)
    def workbench() -> HTMLResponse:
        return HTMLResponse(WORKBENCH_HTML, media_type="text/html; charset=utf-8")

    return app


def _question_payload(record: object) -> dict[str, object]:
    return {
        "research_question_id": record.research_question_id,
        "version": record.version,
        "content_sha256": record.content_sha256,
        "status": record.status,
        "question": record.question.model_dump(mode="json"),
        "created_at": record.created_at.isoformat() + "Z",
    }


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


WORKBENCH_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>研迹 ScholarTrace 证据指挥台</title>
  <style>
    :root { --nav:#0a2740; --nav-2:#103653; --ink:#172536; --muted:#697689; --line:#dce4ea; --paper:#f5f8fa; --card:#fff; --accent:#087f89; --accent-soft:#e8f5f5; --warn:#c76c09; --warn-soft:#fff7ea; --danger:#d84242; --ok:#167b61; --shadow:0 10px 30px rgba(17,44,68,.06); }
    * { box-sizing:border-box; }
    html { min-width:320px; }
    body { margin:0; color:var(--ink); background:var(--paper); font:14px/1.55 Inter,"Segoe UI","Microsoft YaHei",system-ui,sans-serif; }
    button,input,textarea,select { font:inherit; }
    button { min-height:38px; border:1px solid transparent; border-radius:7px; padding:8px 14px; background:var(--accent); color:#fff; font-weight:650; cursor:pointer; transition:.18s ease; }
    button:hover { filter:brightness(.96); transform:translateY(-1px); }
    button:focus-visible,input:focus-visible,textarea:focus-visible,select:focus-visible { outline:3px solid rgba(8,127,137,.22); outline-offset:2px; }
    button:disabled { opacity:.48; cursor:not-allowed; transform:none; }
    button.secondary { color:#26384a; background:#fff; border-color:var(--line); }
    button.ghost { color:var(--accent); background:transparent; }
    button.danger { color:var(--danger); background:#fff; border-color:#f06d6d; }
    input,textarea,select { width:100%; border:1px solid #cbd6df; border-radius:7px; padding:9px 11px; color:var(--ink); background:#fff; }
    textarea { min-height:88px; resize:vertical; }
    label { display:block; margin:11px 0 5px; color:#536173; font-size:12px; font-weight:650; }
    h1,h2,h3,p { margin-top:0; }
    h2 { margin-bottom:8px; font-size:20px; line-height:1.25; } h3 { margin-bottom:10px; font-size:16px; }
    .icon { width:19px; height:19px; flex:none; }
    .side-nav .icon,.mobile-bar .icon { filter:invert(1); opacity:.88; }
    .search .icon { filter:none; opacity:.55; }
    .shell { display:grid; grid-template-columns:200px minmax(0,1fr); min-height:100vh; }
    .sidebar { position:fixed; z-index:30; inset:0 auto 0 0; width:200px; display:flex; flex-direction:column; color:#d7e8f4; background:var(--nav); border-right:1px solid rgba(255,255,255,.1); }
    .brand { height:74px; display:flex; align-items:center; gap:9px; padding:0 18px; color:#fff; border-bottom:1px solid rgba(255,255,255,.12); font-size:18px; font-weight:800; }
    .brand-mark { width:28px; height:28px; display:grid; place-items:center; border:1px solid rgba(117,228,229,.45); border-radius:8px; color:#75e4e5; }
    .side-nav { padding:12px 8px; display:grid; gap:5px; }
    .side-nav button { min-height:48px; display:flex; align-items:center; gap:13px; justify-content:flex-start; color:#dceaf3; background:transparent; border:0; border-radius:7px; text-align:left; }
    .side-nav button.active { color:#fff; background:#126a7a; box-shadow:inset 3px 0 #60d3d7; }
    .side-nav button:hover { background:rgba(255,255,255,.08); transform:none; }
    .researcher { margin:auto 13px 16px; padding:12px; display:flex; align-items:center; gap:10px; border-top:1px solid rgba(255,255,255,.1); font-size:12px; }
    .avatar { width:32px; height:32px; display:grid; place-items:center; border-radius:50%; background:#147d8c; color:#fff; }
    .app { grid-column:2; min-width:0; }
    .topbar { position:sticky; z-index:20; top:0; height:74px; display:grid; grid-template-columns:minmax(230px,330px) minmax(250px,1fr) auto; gap:20px; align-items:center; padding:0 24px; background:rgba(255,255,255,.96); border-bottom:1px solid var(--line); backdrop-filter:blur(10px); }
    .project-switcher { display:flex; align-items:center; gap:10px; min-width:0; }
    .project-switcher span { flex:none; font-weight:700; }
    .project-switcher select { min-width:0; overflow:hidden; text-overflow:ellipsis; }
    .search { position:relative; }
    .search .icon { position:absolute; left:12px; top:10px; color:#77869a; }
    .search input { padding-left:39px; }
    .top-status { display:flex; align-items:center; gap:16px; white-space:nowrap; font-size:13px; }
    .top-status > span { display:flex; align-items:center; gap:7px; }
    .dot { width:8px; height:8px; border-radius:50%; background:#9db1bf; flex:none; }
    .dot.ok { background:#11808a; box-shadow:0 0 0 5px #e9f6f6; }
    .tag { display:inline-flex; align-items:center; width:max-content; border-radius:5px; padding:2px 8px; color:#286173; background:#eaf2f4; font-size:11px; font-weight:650; }
    .tag.candidate { color:#ae6009; background:#fff0d9; } .tag.approved { color:#08705a; background:#e6f5ee; } .tag.rejected { color:#b33838; background:#fdeaea; }
    .content { padding:18px; max-width:1540px; margin:0 auto; }
    .stage-card,.panel { background:var(--card); border:1px solid var(--line); border-radius:9px; box-shadow:var(--shadow); }
    .stage-card { padding:17px 20px; margin-bottom:16px; }
    .stage-card h2 { font-size:16px; margin-bottom:17px; }
    .stage-track { display:grid; grid-template-columns:repeat(6,1fr); position:relative; }
    .stage-track:before { content:""; position:absolute; z-index:0; left:8.5%; right:8.5%; top:12px; height:2px; background:#d5dee5; }
    .stage-step { position:relative; z-index:1; display:grid; justify-items:center; gap:7px; color:#8a95a4; text-align:center; font-size:12px; }
    .stage-step i { width:25px; height:25px; display:grid; place-items:center; border:2px solid #bfccd6; border-radius:50%; background:#fff; font-style:normal; }
    .stage-step.done,.stage-step.active { color:#26384a; }
    .stage-step.done i { color:#fff; background:var(--accent); border-color:var(--accent); }
    .stage-step.active i { color:var(--accent); border-color:var(--accent); box-shadow:inset 0 0 0 4px #fff; background:#bfe2e4; }
    .stage-step.active:after { content:""; position:absolute; bottom:-14px; width:44px; height:3px; border-radius:5px; background:var(--accent); }
    .workspace-grid { display:grid; grid-template-columns:minmax(0,1fr) 345px; gap:16px; align-items:start; }
    .primary { min-width:0; }
    .detail-panel { position:sticky; top:92px; min-height:calc(100vh - 110px); padding:18px 20px; }
    .panel { padding:18px 20px; margin-bottom:16px; }
    .panel-head { display:flex; justify-content:space-between; gap:18px; align-items:flex-start; }
    .eyebrow { display:flex; align-items:center; gap:8px; margin-bottom:5px; color:#8c510d; font-size:12px; font-weight:750; }
    .eyebrow .dot { background:#cb720d; box-shadow:none; }
    .muted { color:var(--muted); } .error { color:#b33c3c; white-space:pre-wrap; } .success { color:var(--ok); }
    .hidden { display:none !important; }
    .queue { margin-top:14px; border:1px solid var(--line); border-radius:7px; overflow:hidden; }
    .queue-row { display:grid; grid-template-columns:28px minmax(170px,1fr) minmax(150px,.45fr) 82px 90px; gap:12px; align-items:center; min-height:48px; padding:9px 12px; border-bottom:1px solid var(--line); cursor:pointer; }
    .queue-row:last-child { border-bottom:0; } .queue-row:hover,.queue-row.selected { background:#f2f8f8; }
    .queue-row .title { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font-weight:620; }
    .queue-row .source-id { color:#416a87; font-size:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .queue-row input { width:16px; height:16px; accent-color:var(--accent); }
    .queue-foot { display:flex; align-items:center; gap:25px; margin-top:16px; min-height:40px; }
    .queue-foot button { margin-left:auto; }
    .legend { display:flex; gap:18px; color:#354454; font-size:12px; }
    .legend span { display:flex; align-items:center; gap:7px; }
    .legend .dot { width:7px; height:7px; box-shadow:none; }
    .dashboard-row { display:grid; grid-template-columns:1fr 1.05fr; gap:16px; }
    .gap-list,.run-summary { display:grid; gap:0; }
    .gap-item { display:grid; grid-template-columns:minmax(0,1fr) 44px 70px; gap:9px; padding:11px 0; border-bottom:1px solid #edf1f4; align-items:center; font-size:12px; }
    .priority { width:27px; height:22px; display:grid; place-items:center; border-radius:4px; background:#fff1d9; color:#af620b; font-weight:700; }
    .priority.high { background:#fde8e8; color:#c43a3a; } .priority.low { background:#e7f4ec; color:#277457; }
    .run-item { position:relative; display:grid; grid-template-columns:minmax(0,1fr) auto; gap:4px 15px; padding:10px 0 10px 24px; border-left:2px solid #c4dbe0; }
    .run-item:before { content:""; position:absolute; width:9px; height:9px; left:-6px; top:17px; border:2px solid #fff; border-radius:50%; background:var(--accent); box-shadow:0 0 0 1px var(--accent); }
    .run-item b { font-size:12px; } .run-item small { color:var(--muted); }
    .detail-alert { padding:13px; border:1px solid #f0cda0; border-radius:7px; background:var(--warn-soft); }
    .detail-alert b { display:block; color:#915411; margin-bottom:3px; }
    .detail-fields { display:grid; gap:14px; margin:18px 0; }
    .detail-field dt { color:#677487; font-size:12px; } .detail-field dd { margin:2px 0 0; color:#253649; overflow-wrap:anywhere; }
    .abstract { padding-top:14px; border-top:1px solid var(--line); }
    .review-actions { display:grid; grid-template-columns:1fr 1fr; gap:9px; margin-top:13px; }
    .review-actions .wide { grid-column:1/-1; }
    .empty { padding:26px 12px; color:var(--muted); text-align:center; }
    .metric-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; }
    .metric { padding:14px; border:1px solid var(--line); border-radius:8px; background:#fbfcfd; }
    .metric strong { display:block; font-size:24px; color:var(--accent); }
    .split { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
    .question-editor { display:grid; grid-template-columns:1fr 1fr; gap:12px 14px; }
    .question-editor .wide { grid-column:1/-1; }
    .candidate-banner { margin:12px 0; padding:11px 13px; border-left:3px solid var(--warn); background:var(--warn-soft); }
    .row { display:flex; flex-wrap:wrap; gap:9px; align-items:center; }
    .timeline { border-left:2px solid #bfd2d8; margin:15px 0 0 7px; padding-left:18px; }
    .event { position:relative; margin:0 0 14px; } .event:before { content:""; position:absolute; width:8px; height:8px; left:-23px; top:7px; border-radius:50%; background:var(--accent); }
    pre { padding:14px; overflow:auto; border-radius:7px; color:#deedf4; background:#102a43; white-space:pre-wrap; }
    .mobile-bar { display:none; }
    @media(max-width:1100px) { .workspace-grid{grid-template-columns:minmax(0,1fr) 305px}.queue-row{grid-template-columns:25px minmax(150px,1fr) 80px 90px}.queue-row .source-id{display:none}.topbar{grid-template-columns:minmax(220px,1fr) auto}.search{display:none}.dashboard-row{grid-template-columns:1fr}.detail-panel{padding:16px} }
    @media(max-width:820px) { .shell{display:block}.sidebar{display:none}.app{grid-column:auto}.topbar{height:auto;min-height:68px;padding:10px 14px;grid-template-columns:1fr}.top-status{justify-content:space-between;gap:8px;font-size:11px}.project-switcher span{display:none}.content{padding:12px 12px 80px}.workspace-grid{grid-template-columns:1fr}.detail-panel{position:static;min-height:0}.stage-card{overflow:auto}.stage-track{min-width:620px}.dashboard-row,.split,.question-editor{grid-template-columns:1fr}.question-editor .wide{grid-column:auto}.queue-row{grid-template-columns:24px minmax(0,1fr) 92px}.queue-row .source-id,.queue-row .score{display:none}.metric-grid{grid-template-columns:repeat(2,1fr)}.mobile-bar{display:grid;position:fixed;z-index:40;bottom:0;left:0;right:0;grid-template-columns:repeat(6,1fr);padding:7px 5px max(7px,env(safe-area-inset-bottom));background:#09263f;border-top:1px solid rgba(255,255,255,.12)}.mobile-bar button{min-height:48px;padding:4px;color:#cfe0eb;background:transparent;font-size:10px}.mobile-bar button.active{color:#75e4e5}.mobile-bar .icon{display:block;margin:0 auto 2px;width:18px}.panel-head{display:block}.panel-head .row{margin-top:12px}.review-actions{grid-template-columns:1fr}.review-actions .wide{grid-column:auto} }
  </style>
</head>
<body>
  <div class="shell">
    <aside class="sidebar" aria-label="主导航">
      <div class="brand"><span class="brand-mark">研</span><span>研迹 ScholarTrace</span></div>
      <nav class="side-nav">
        <button data-tab="overview" class="active"><img class="icon" src="/static/icons/layout-dashboard.png" alt="">总览</button>
        <button data-tab="question"><img class="icon" src="/static/icons/help-circle.png" alt="">研究问题</button>
        <button data-tab="literature"><img class="icon" src="/static/icons/book-2.png" alt="">文献与证据</button>
        <button data-tab="experiments"><img class="icon" src="/static/icons/flask.png" alt="">实验与 Run</button>
        <button data-tab="figures"><img class="icon" src="/static/icons/chart-line.png" alt="">图表</button>
        <button data-tab="manuscript"><img class="icon" src="/static/icons/file-text.png" alt="">论文草稿</button>
      </nav>
      <div class="researcher"><span class="avatar">研</span><span><b>研究员</b><br><span style="opacity:.65">本地工作区</span></span></div>
    </aside>
    <section class="app">
      <header class="topbar">
        <div class="project-switcher"><span>项目</span><select id="project-switch" aria-label="当前项目"><option value="">选择或创建项目</option></select></div>
        <div class="search"><img class="icon" src="/static/icons/search.png" alt=""><input id="global-search" type="search" placeholder="搜索研究内容、文献、Run…" aria-label="筛选当前视图"></div>
        <div class="top-status"><span>当前阶段：<b id="header-stage">未连接</b><i class="dot"></i></span><span>研究助手 · <b id="llm-model">未配置</b><i id="llm-dot" class="dot"></i></span><span id="llm-status" class="tag">离线</span></div>
      </header>
      <main class="content">
        <section id="workspace">
          <section class="stage-card"><h2>研究阶段</h2><div class="stage-track" id="stage-track"><div class="stage-step active"><i>1</i><span>问题定义</span></div><div class="stage-step"><i>2</i><span>证据检索</span></div><div class="stage-step"><i>3</i><span>证据审阅</span></div><div class="stage-step"><i>4</i><span>实验验证</span></div><div class="stage-step"><i>5</i><span>结果分析</span></div><div class="stage-step"><i>6</i><span>论文撰写</span></div></div></section>
          <div class="workspace-grid"><div class="primary">
            <div id="overview" class="tab">
              <section id="start" class="panel">
                <div class="panel-head"><div><div class="eyebrow"><i class="dot"></i>建立本地研究工作区</div><h2>把研究过程放进可追溯的证据链</h2><p class="muted">先创建项目，再由你决定是否保存研究问题。合成/脱敏数据不代表真实科研证据。</p></div><span class="tag">local-first</span></div>
                <form id="project-form"><div class="split"><div><label for="project-id">项目 ID</label><input id="project-id" value="lychee-vision-demo" pattern="[A-Za-z0-9._-]+" required></div><div><label for="thread-id">Thread ID</label><input id="thread-id" value="thread-lychee-vision-demo" pattern="[A-Za-z0-9._-]+" required></div></div><label for="goal">当前目标</label><input id="goal" value="定义可检验的农业视觉研究问题"><div class="row" style="margin-top:14px"><button id="open-project" type="submit">创建 / 打开工作区</button><span id="start-error" class="error" role="alert"></span></div></form>
              </section>
              <section class="panel"><div class="panel-head"><div><div class="eyebrow"><i class="dot"></i>需要你处理</div><h2 id="queue-title">候选文献审批队列</h2><p id="project-meta" class="muted">研究助手找到的候选只会在人工决定后进入证据库。</p></div><div class="row"><span id="project-stage" class="tag"></span><button id="refresh" class="secondary" title="刷新项目状态"><img class="icon" src="/static/icons/refresh.png" alt="刷新"></button></div></div><div id="literature-queue" class="queue"><div class="empty">暂无候选文献。</div></div><div class="queue-foot"><div id="queue-legend" class="legend"></div><button id="open-selected" disabled>查看并审批</button></div></section>
              <div class="dashboard-row"><section class="panel"><h3>证据缺口</h3><div id="evidence-gaps" class="gap-list"></div></section><section class="panel"><h3>最近 Run</h3><div id="run-summary" class="run-summary"></div></section></div>
              <section id="counts" class="metric-grid"></section>
              <section class="panel"><h3 id="project-title">当前项目</h3><p class="muted">工作台边界：合成/脱敏数据只用于演示状态流和追溯协议；没有来源的 Claim 会保留为待验证，不会被页面自动升级。</p></section>
            </div>
            <div id="question" class="tab hidden"><section class="panel"><div class="panel-head"><div><h2>研究问题</h2><p class="muted">研究助手只能生成未经验证的 candidate，正式保存始终由你触发。</p></div><span id="candidate-status" class="tag">manual</span></div><div class="question-editor"><div class="wide"><label for="problem">研究问题</label><textarea id="problem">如何在荔枝果园图像中稳定识别病虫害并保持评估结果可追溯？</textarea></div><div><label for="question-context">给研究助手的上下文（可选）</label><textarea id="question-context" placeholder="仅填写允许发送给 Provider 的非敏感上下文"></textarea></div><div><label for="target-domain">目标域</label><textarea id="target-domain">荔枝果园农业视觉图像</textarea></div><div><label for="question-inputs">输入（每行一项）</label><textarea id="question-inputs">田间图像</textarea></div><div><label for="question-outputs">预期输出（每行一项）</label><textarea id="question-outputs">病虫害类别与定位</textarea></div><div><label for="question-constraints">约束（每行一项）</label><textarea id="question-constraints">保留数据版本和采集协议</textarea></div><div><label for="question-criteria">成功标准（每行一项）</label><textarea id="question-criteria">验证集指标可独立重算</textarea></div><div><label for="question-assumptions">假设（每行一项）</label><textarea id="question-assumptions">Fixture 仅用于离线演示</textarea></div><div><label for="question-unresolved">未决问题（每行一项）</label><textarea id="question-unresolved">真实场景采集伦理待确认</textarea></div></div><div id="candidate-warning" class="candidate-banner hidden">candidate 未经验证、不会自动保存。请逐字段复核，不代表引用、指标、审批或科研结论。</div><div class="row"><button id="generate-candidate" class="secondary">生成 GLM 候选</button><button id="save-question">正式保存研究问题</button><span id="question-error" class="error" role="alert"></span></div></section><section class="panel"><h3>已保存版本</h3><div id="question-list" class="muted">尚未保存研究问题。</div></section></div>
            <div id="literature" class="tab hidden"><section class="panel"><div class="panel-head"><div><h2>文献与证据</h2><p class="muted">只有明确批准且可搜索的项目文献才会进入证据链。</p></div><button id="literature-review" class="secondary">打开审批队列</button></div><div class="metric-grid"><div class="metric"><strong id="documents-count">0</strong>已批准文献</div><div class="metric"><strong id="candidate-count">0</strong>候选文献</div><div class="metric"><strong id="evidence-count">0</strong>EvidenceCard</div></div><div id="literature-list" style="margin-top:14px"></div></section></div>
            <div id="experiments" class="tab hidden"><section class="panel"><h2>实验与 Run 时间线</h2><div id="runs-list" class="muted">暂无受控 Run。</div><div id="timeline" class="timeline"></div></section></div>
            <div id="manuscript" class="tab hidden"><section class="panel"><div class="panel-head"><div><h2>论文草稿</h2><p class="muted">确定性模板保留 Claim、MetricResult 和 citation 来源标记。</p></div><div class="row"><button id="create-manuscript">生成论文草稿契约</button><button id="submit-review" class="secondary" disabled>提交人工审阅</button></div></div><div id="manuscript-state" class="muted">尚未创建 Manuscript。</div><div id="draft-sections"></div></section></div>
            <div id="figures" class="tab hidden"><section class="panel"><h2>图表与 Artifact</h2><div id="figures-list" class="muted">暂无图表。</div></section></div>
          </div><aside id="evidence-detail" class="detail-panel panel" aria-live="polite"><h2>证据详情</h2><div id="detail-content" class="empty">从候选队列中选择一条文献，查看来源元数据并作出人工决定。</div></aside></div>
        </section>
      </main>
    </section>
  </div>
  <nav class="mobile-bar" aria-label="移动端导航"><button data-tab="overview" class="active"><img class="icon" src="/static/icons/layout-dashboard.png" alt="">总览</button><button data-tab="question"><img class="icon" src="/static/icons/help-circle.png" alt="">问题</button><button data-tab="literature"><img class="icon" src="/static/icons/book-2.png" alt="">文献</button><button data-tab="experiments"><img class="icon" src="/static/icons/flask.png" alt="">Run</button><button data-tab="figures"><img class="icon" src="/static/icons/chart-line.png" alt="">图表</button><button data-tab="manuscript"><img class="icon" src="/static/icons/file-text.png" alt="">论文</button></nav>
  <script>
    const state = { projectId:null, manuscript:null, projectDocuments:[], selectedDocumentId:null, timelineEvents:new Map(), eventSources:new Map(), llmEnabled:false };
    const $ = (id) => document.getElementById(id);
    const listValue = (id) => $(id).value.split(String.fromCharCode(10)).map((value) => value.trim()).filter(Boolean);
    function escapeHTML(value) { return String(value ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;'); }
    function displayDate(value) { if (!value) return '—'; const parsed = new Date(value); return Number.isNaN(parsed.valueOf()) ? value : parsed.toLocaleString('zh-CN',{dateStyle:'medium',timeStyle:'short'}); }
    async function request(path, options={}) { const response=await fetch(path,{headers:{'Content-Type':'application/json'},...options}); const body=await response.json().catch(()=>({})); if(!response.ok) throw new Error(body.detail || ('HTTP '+response.status)); return body; }
    function showTab(name) { document.querySelectorAll('.tab').forEach((node)=>node.classList.toggle('hidden',node.id!==name)); document.querySelectorAll('[data-tab]').forEach((node)=>node.classList.toggle('active',node.dataset.tab===name)); }
    function stageIndex(data) { if(data.manuscripts.length) return 5; if(data.figures.length) return 4; if(data.runs.length) return 3; if(data.projectDocuments.length) return 2; if(data.questions.length) return 1; return 0; }
    function renderStage(index) { const labels=['问题定义','证据检索','证据审阅','实验验证','结果分析','论文撰写']; $('header-stage').textContent=labels[index]; $('project-stage').textContent=labels[index]; document.querySelectorAll('.stage-step').forEach((node,step)=>{ node.classList.toggle('done',step<index); node.classList.toggle('active',step===index); node.querySelector('i').textContent=step<index?'✓':String(step+1); }); }
    function renderCounts(data) { $('counts').innerHTML=[['研究问题',data.questions.length],['项目文献',data.projectDocuments.length],['证据卡',data.evidence.length],['受控 Run',data.runs.length],['论文版本',data.manuscripts.length],['图表',data.figures.length]].map(([label,value])=>`<div class="metric"><strong>${escapeHTML(value)}</strong>${escapeHTML(label)}</div>`).join(''); }
    function renderQuestion(items) { $('question-list').innerHTML=items.length?items.slice().reverse().map((item)=>`<article style="padding:12px 0;border-bottom:1px solid var(--line)"><span class="tag">v${escapeHTML(item.version)} · ${escapeHTML(item.status)}</span><p style="margin:8px 0 3px"><b>${escapeHTML(item.question.problem)}</b></p><p class="muted">目标域：${escapeHTML(item.question.target_population_or_domain)}<br>成功标准：${escapeHTML(item.question.success_criteria.join('；'))}</p></article>`).join(''):'尚未保存研究问题。'; }
    function documentTitle(item) { return item.document.metadata.title || item.document.document_id; }
    function renderLiterature(items) { const counts={candidate:0,approved:0,rejected:0}; items.forEach((item)=>counts[item.link.status]++); $('candidate-count').textContent=counts.candidate; $('documents-count').textContent=counts.approved; $('queue-title').textContent=counts.candidate?`批准 ${counts.candidate} 条候选文献`:'候选文献审批队列'; $('queue-legend').innerHTML=`<span><i class="dot" style="background:#c97512"></i>候选 ${counts.candidate}</span><span><i class="dot" style="background:#168068"></i>已批准 ${counts.approved}</span><span><i class="dot" style="background:#d84242"></i>已拒绝 ${counts.rejected}</span>`; const visible=items.filter((item)=>item.link.status==='candidate'); $('literature-queue').innerHTML=visible.length?visible.map((item)=>`<div class="queue-row${item.document.document_id===state.selectedDocumentId?' selected':''}" data-document-id="${escapeHTML(item.document.document_id)}"><input type="radio" name="candidate-document" aria-label="选择 ${escapeHTML(documentTitle(item))}" ${item.document.document_id===state.selectedDocumentId?'checked':''}><span class="title">${escapeHTML(documentTitle(item))}</span><span class="source-id">${escapeHTML(item.document.document_id)}</span><span>${escapeHTML(item.document.source_type)}</span><span class="score">${item.link.relevance_score==null?'待评分':'相关度 '+escapeHTML(item.link.relevance_score)}</span></div>`).join(''):'<div class="empty">暂无待审批候选；已作出的决定不会在这里重复开放。</div>'; $('literature-list').innerHTML=items.length?items.map((item)=>`<article style="padding:12px 0;border-bottom:1px solid var(--line)" data-searchable-text="${escapeHTML((documentTitle(item)+' '+item.document.document_id).toLowerCase())}"><span class="tag ${escapeHTML(item.link.status)}">${escapeHTML(item.link.status)}</span> <b>${escapeHTML(documentTitle(item))}</b><div class="muted">${escapeHTML(item.document.metadata.authors.join('、')||'作者未记录')} · ${escapeHTML(item.document.metadata.year||'年份未记录')} · ${escapeHTML(item.document.document_id)}</div></article>`).join(''):'<div class="empty">项目尚未关联文献。</div>'; document.querySelectorAll('.queue-row').forEach((row)=>row.addEventListener('click',()=>selectDocument(row.dataset.documentId))); $('open-selected').disabled=!state.selectedDocumentId; }
    function selectDocument(id) { state.selectedDocumentId=id; renderLiterature(state.projectDocuments); renderDetail(); }
    function renderDetail() { const item=state.projectDocuments.find((entry)=>entry.document.document_id===state.selectedDocumentId); if(!item){ $('detail-content').innerHTML='<div class="empty">从候选队列中选择一条文献，查看来源元数据并作出人工决定。</div>'; return; } const meta=item.document.metadata; const source=meta.doi?`DOI ${meta.doi}`:(meta.url||item.document.storage_relpath||'未记录可跳转来源'); const canReview=item.link.status==='candidate'; $('detail-content').innerHTML=`<div class="detail-alert"><b>${canReview?'候选内容，需人工确认':'该文献已有人工决定'}</b><span>${canReview?'请核对内容与来源信息后决定是否纳入证据库。':'状态：'+escapeHTML(item.link.status)+'；如需变更，请通过受控审批流程处理。'}</span></div><dl class="detail-fields"><div class="detail-field"><dt>标题</dt><dd><b>${escapeHTML(documentTitle(item))}</b></dd></div><div class="detail-field"><dt>来源 ID</dt><dd>${escapeHTML(item.document.document_id)}</dd></div><div class="detail-field"><dt>来源类型</dt><dd>${escapeHTML(item.document.source_type)} · ${item.document.searchable?'可搜索':'不可搜索'}</dd></div><div class="detail-field"><dt>作者</dt><dd>${escapeHTML(meta.authors.join('、')||'未记录')}</dd></div><div class="detail-field"><dt>年份 / 来源</dt><dd>${escapeHTML(meta.year||'未记录')} · ${escapeHTML(source)}</dd></div></dl><div class="abstract"><label>摘要</label><p>${escapeHTML(meta.abstract||'暂无摘要；请从可核验来源补齐后再作为正式证据使用。')}</p></div>${canReview?`<label for="review-reason">审批理由</label><textarea id="review-reason" placeholder="记录你的判断依据（必填）"></textarea><label for="review-score">相关度评分（0–1，可选）</label><input id="review-score" type="number" min="0" max="1" step="0.01" value="${item.link.relevance_score??''}"><div class="review-actions"><button id="approve-document">✓ 批准纳入</button><button id="reject-document" class="danger">拒绝</button><span id="review-error" class="error wide" role="alert"></span></div>`:`<p class="muted">决定人：${escapeHTML(item.link.decided_by||'未记录')}<br>理由：${escapeHTML(item.link.relevance_reason||'未记录')}<br>时间：${escapeHTML(displayDate(item.link.decided_at))}</p>`}`; if(canReview){ $('approve-document').addEventListener('click',()=>reviewDocument('approved')); $('reject-document').addEventListener('click',()=>reviewDocument('rejected')); } }
    async function reviewDocument(status) { const reason=$('review-reason').value.trim(); if(!reason){ $('review-error').textContent='请先填写审批理由。'; return; } const raw=$('review-score').value; const relevance_score=raw===''?null:Number(raw); try { await request(`/api/projects/${encodeURIComponent(state.projectId)}/project-documents/${encodeURIComponent(state.selectedDocumentId)}/review`,{method:'POST',body:JSON.stringify({status,actor_id:'workbench-user',reason,relevance_score})}); state.selectedDocumentId=null; await refresh(); } catch(error){ $('review-error').textContent=error.message; } }
    function renderGaps(data) { const gaps=[]; if(!data.questions.length) gaps.push(['研究问题尚未正式保存','高','high']); if(!data.documents.length) gaps.push(['没有人工批准的文献','高','high']); if(!data.evidence.length) gaps.push(['尚无已验证 EvidenceCard','中','']); if(!data.runs.length) gaps.push(['尚无受控实验 Run','中','']); if(!data.figures.length) gaps.push(['尚无可追溯图表','低','low']); $('evidence-gaps').innerHTML=gaps.length?gaps.map(([label,priority,kind],index)=>`<div class="gap-item"><span>${escapeHTML(label)}</span><span class="priority ${kind}">${priority}</span><span class="source-id">GAP-${String(index+1).padStart(3,'0')}</span></div>`).join(''):'<div class="empty">当前核心证据链没有结构性缺口。</div>'; }
    function renderRuns(runs) { $('runs-list').innerHTML=runs.length?runs.map((run)=>`<article style="padding:12px 0;border-bottom:1px solid var(--line)"><span class="tag">${escapeHTML(run.status)}</span> <b>${escapeHTML(run.execution_id)}</b><span class="muted"> · ${escapeHTML(run.backend)} · ${escapeHTML(run.plan_id)}</span></article>`).join(''):'暂无受控 Run。'; $('run-summary').innerHTML=runs.length?runs.slice(-4).reverse().map((run)=>`<div class="run-item"><b>${escapeHTML(run.execution_id)}</b><span class="tag">${escapeHTML(run.status)}</span><small>${escapeHTML(run.plan_id)} · ${escapeHTML(run.backend)}</small><small>${escapeHTML(displayDate(run.created_at))}</small></div>`).join(''):'<div class="empty">Run 会在计划冻结并受控执行后显示。</div>'; }
    function renderTimeline() { const events=[...state.timelineEvents.values()].sort((a,b)=>a.created_at.localeCompare(b.created_at)||a.sequence-b.sequence); $('timeline').innerHTML=events.length?events.map((event)=>`<div class="event"><b>${escapeHTML(event.execution_id)}</b> <span class="tag">${escapeHTML(event.stream)}</span><div>${escapeHTML(event.message)}</div><small>#${escapeHTML(event.sequence)} · ${escapeHTML(displayDate(event.created_at))}</small></div>`).join(''):'<span class="muted">暂无 Run 事件。</span>'; }
    function consumeRunEvent(event) { try { const payload=JSON.parse(event.data); state.timelineEvents.set(`${payload.execution_id}:${payload.sequence}`,payload); renderTimeline(); } catch(error){ $('timeline').innerHTML=`<span class="error">无法解析 Run 事件：${escapeHTML(error.message)}</span>`; } }
    function openRunStream(run) { const previous=state.eventSources.get(run.execution_id); if(previous)previous.close(); const known=[...state.timelineEvents.values()].filter((event)=>event.execution_id===run.execution_id); const after=known.reduce((latest,event)=>Math.max(latest,event.sequence),-1); const source=new EventSource(`/api/projects/${encodeURIComponent(state.projectId)}/runs/${encodeURIComponent(run.execution_id)}/events/stream?after_sequence=${after}&live=true`); ['stdout','stderr','system'].forEach((stream)=>source.addEventListener(stream,consumeRunEvent)); source.onerror=()=>{ if(source.readyState===EventSource.CLOSED)state.eventSources.delete(run.execution_id); }; state.eventSources.set(run.execution_id,source); }
    async function refreshTimeline(runs) { state.eventSources.forEach((source)=>source.close()); state.eventSources.clear(); state.timelineEvents.clear(); for(const run of runs){ try { const events=await request(`/api/projects/${encodeURIComponent(state.projectId)}/runs/${encodeURIComponent(run.execution_id)}/events`); events.forEach((event)=>state.timelineEvents.set(`${event.execution_id}:${event.sequence}`,event)); } catch(error){ $('timeline').innerHTML=`<span class="error">无法加载 ${escapeHTML(run.execution_id)} 的事件：${escapeHTML(error.message)}</span>`; } } renderTimeline(); runs.forEach(openRunStream); }
    function renderDraft(draft) { $('manuscript-state').innerHTML=`<span class="tag">${escapeHTML(state.manuscript.status)}</span> <b>${escapeHTML(state.manuscript.title)}</b>`; $('submit-review').disabled=state.manuscript.status!=='draft'; $('draft-sections').innerHTML=draft.errors.map((error)=>`<p class="error">${escapeHTML(error)}</p>`).join('')+draft.sections.map((section)=>`<article class="panel"><h3>${escapeHTML(section.section_id)}</h3><pre>${escapeHTML(section.markdown)}</pre></article>`).join(''); }
    async function loadLLMStatus() { try { const status=await request('/api/llm/status'); state.llmEnabled=status.enabled; $('llm-model').textContent=status.model||'未配置'; $('llm-status').textContent=status.enabled?'在线':'离线'; $('llm-dot').classList.toggle('ok',status.enabled); $('generate-candidate').disabled=!status.enabled; $('generate-candidate').textContent=status.enabled?'生成 GLM 候选':'LLM 未配置 · 使用手工录入'; } catch(error){ state.llmEnabled=false; $('llm-status').textContent='不可用'; $('generate-candidate').disabled=true; } }
    async function loadProjects() { try { const projects=await request('/api/projects'); $('project-switch').innerHTML='<option value="">选择或创建项目</option>'+projects.map((project)=>`<option value="${escapeHTML(project.project_id)}" ${project.project_id===state.projectId?'selected':''}>${escapeHTML(project.project_id)}</option>`).join(''); } catch(error){ $('start-error').textContent=error.message; } }
    async function refresh() { if(!state.projectId)return; try { const id=encodeURIComponent(state.projectId); const [project,questions,documents,projectDocuments,evidence,runs,manuscripts,figures]=await Promise.all([request(`/api/projects/${id}`),request(`/api/projects/${id}/research-questions`),request(`/api/projects/${id}/documents`),request(`/api/projects/${id}/project-documents`),request(`/api/projects/${id}/evidence`),request(`/api/projects/${id}/runs`),request(`/api/projects/${id}/manuscripts`),request(`/api/projects/${id}/figures`)]); state.projectDocuments=projectDocuments; if(state.selectedDocumentId&&!projectDocuments.some((item)=>item.document.document_id===state.selectedDocumentId))state.selectedDocumentId=null; $('project-title').textContent=project.project_id; $('project-meta').textContent=project.current_goal||'研究助手找到的候选只会在人工决定后进入证据库。'; renderStage(stageIndex({questions,projectDocuments,runs,figures,manuscripts})); renderQuestion(questions); renderLiterature(projectDocuments); renderDetail(); renderRuns(runs); void refreshTimeline(runs); $('evidence-count').textContent=evidence.length; $('figures-list').textContent=figures.length?`${figures.length} 个 FigureSpec 已保存`:'暂无图表。'; renderCounts({questions,projectDocuments,evidence,runs,manuscripts,figures}); renderGaps({questions,documents,evidence,runs,figures}); if(manuscripts.length){ state.manuscript=manuscripts[manuscripts.length-1]; const draft=await request(`/api/projects/${id}/manuscripts/${state.manuscript.manuscript_id}/draft`); renderDraft(draft); } await loadProjects(); } catch(error){ $('start-error').textContent=error.message; } }
    function questionPayload() { return {problem:$('problem').value.trim(),target_population_or_domain:$('target-domain').value.trim(),inputs:listValue('question-inputs'),expected_outputs:listValue('question-outputs'),constraints:listValue('question-constraints'),success_criteria:listValue('question-criteria'),assumptions:listValue('question-assumptions'),unresolved_questions:listValue('question-unresolved')}; }
    function fillCandidate(candidate) { const mapping={problem:'problem',target_population_or_domain:'target-domain',inputs:'question-inputs',expected_outputs:'question-outputs',constraints:'question-constraints',success_criteria:'question-criteria',assumptions:'question-assumptions',unresolved_questions:'question-unresolved'}; Object.entries(mapping).forEach(([field,id])=>{ $(id).value=Array.isArray(candidate[field])?candidate[field].join(String.fromCharCode(10)):(candidate[field]||''); }); $('candidate-status').className='tag candidate'; $('candidate-status').textContent='candidate'; $('candidate-warning').classList.remove('hidden'); }
    async function openProject(projectId) { state.projectId=projectId; $('project-id').value=projectId; $('start').classList.add('hidden'); $('workspace').classList.remove('hidden'); history.replaceState(null,'',`?project=${encodeURIComponent(projectId)}`); await refresh(); }
    $('project-form').addEventListener('submit',async(event)=>{ event.preventDefault(); $('start-error').textContent=''; try { const projectId=$('project-id').value.trim(); await request('/api/projects',{method:'POST',body:JSON.stringify({project_id:projectId,thread_id:$('thread-id').value.trim(),current_goal:$('goal').value.trim()||null})}); await openProject(projectId); showTab('question'); } catch(error){ $('start-error').textContent=error.message; } });
    $('generate-candidate').addEventListener('click',async()=>{ $('question-error').textContent=''; if(!state.projectId){ $('question-error').textContent='请先在“总览”标签创建或打开项目。'; return; } const button=$('generate-candidate'); button.disabled=true; button.textContent='正在生成候选…'; try { const response=await request(`/api/projects/${encodeURIComponent(state.projectId)}/research-question-candidates`,{method:'POST',body:JSON.stringify({problem:$('problem').value.trim(),context:$('question-context').value.trim()||null})}); fillCandidate(response.candidate); } catch(error){ $('question-error').textContent=`研究助手不可用：${error.message}。你仍可手工填写并保存。`; } finally { button.disabled=!state.llmEnabled; button.textContent=state.llmEnabled?'生成 GLM 候选':'LLM 未配置 · 使用手工录入'; } });
    $('save-question').addEventListener('click',async()=>{ $('question-error').textContent=''; if(!state.projectId){ $('question-error').textContent='请先在“总览”标签创建或打开项目。'; return; } try { await request(`/api/projects/${encodeURIComponent(state.projectId)}/research-questions`,{method:'POST',body:JSON.stringify(questionPayload())}); $('candidate-status').className='tag approved'; $('candidate-status').textContent='已正式保存'; $('candidate-warning').classList.add('hidden'); await refresh(); } catch(error){ $('question-error').textContent=error.message; } });
    $('refresh').addEventListener('click',refresh); $('open-selected').addEventListener('click',()=>{ if(state.selectedDocumentId)$('evidence-detail').scrollIntoView({behavior:'smooth',block:'start'}); }); $('literature-review').addEventListener('click',()=>{ showTab('overview'); $('literature-queue').scrollIntoView({behavior:'smooth',block:'center'}); });
    $('create-manuscript').addEventListener('click',async()=>{ if(!state.projectId){ $('manuscript-state').textContent='请先在“总览”标签创建或打开项目。'; return; } try { await request(`/api/projects/${encodeURIComponent(state.projectId)}/manuscripts`,{method:'POST',body:JSON.stringify({title:'可追溯科研论文草稿',target_template:'journal_article'})}); await refresh(); showTab('manuscript'); } catch(error){ $('manuscript-state').textContent=error.message; } }); $('submit-review').addEventListener('click',async()=>{ if(!state.projectId||!state.manuscript){ $('manuscript-state').textContent='请先创建项目并生成论文草稿契约。'; return; } try { await request(`/api/projects/${encodeURIComponent(state.projectId)}/manuscripts/${state.manuscript.manuscript_id}/review`,{method:'POST',body:JSON.stringify({actor_id:'workbench-user',reason:'从工作台提交人工审阅'})}); await refresh(); } catch(error){ $('manuscript-state').textContent=error.message; } });
    document.querySelectorAll('[data-tab]').forEach((button)=>button.addEventListener('click',()=>showTab(button.dataset.tab))); $('project-switch').addEventListener('change',()=>{ if($('project-switch').value)openProject($('project-switch').value); }); $('global-search').addEventListener('input',()=>{ const query=$('global-search').value.trim().toLowerCase(); document.querySelectorAll('[data-searchable-text]').forEach((node)=>node.classList.toggle('hidden',query&&!node.dataset.searchableText.includes(query))); });
    const initialProject=new URLSearchParams(location.search).get('project'); void loadLLMStatus(); void loadProjects(); if(initialProject)openProject(initialProject);
  </script>
</body>
</html>"""
