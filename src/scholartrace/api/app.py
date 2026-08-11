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

from scholartrace import __version__
from scholartrace.inference import InferenceContractError, InferenceService
from scholartrace.manuscript import SectionGenerationError, generate_section_draft
from scholartrace.persistence.evidence_repository import EvidenceRepository
from scholartrace.persistence.figure_repository import FigureRepository
from scholartrace.persistence.literature_repository import LiteratureRepository
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
    Manuscript,
    ManuscriptCreateRequest,
    ManuscriptDraftResponse,
    ManuscriptReviewRequest,
    ProjectCreateRequest,
    ProjectResponse,
    ResearchQuestion,
    SectionContract,
)


def create_app(
    database_path: Path | None = None,
    *,
    delivery_root: Path | None = None,
    delivery_manifest_path: Path | None = None,
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
    inference_service: InferenceService | None = None
    if delivery_root is not None or delivery_manifest_path is not None:
        if delivery_root is None or delivery_manifest_path is None:
            raise ValueError("delivery_root and delivery_manifest_path must be supplied together")
        manifest = DeliveryManifest.model_validate_json(
            delivery_manifest_path.read_text(encoding="utf-8")
        )
        inference_service = InferenceService(delivery_root, manifest)
    app = FastAPI(title="研迹 ScholarTrace API", version=__version__)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

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
        except (ProjectNotFoundError, ValueError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return _question_payload(record)

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
  <title>研迹 ScholarTrace 工作台</title>
  <style>
    :root { --ink:#17212b; --muted:#64727e; --line:#dbe3e8; --paper:#f7fafb; --accent:#177e89; --accent-2:#e8f5f3; --warn:#fff4dc; }
    * { box-sizing:border-box; }
    body { margin:0; color:var(--ink); background:var(--paper); font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif; }
    header { background:#102a43; color:white; padding:24px clamp(20px,5vw,72px); display:flex; justify-content:space-between; align-items:end; gap:24px; }
    header h1 { margin:0; font-size:28px; letter-spacing:.02em; } header p { margin:4px 0 0; color:#c8d8e3; }
    main { max-width:1240px; margin:28px auto; padding:0 20px; }
    .panel { background:white; border:1px solid var(--line); border-radius:14px; padding:22px; box-shadow:0 8px 24px #102a4308; margin-bottom:18px; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:14px; }
    .metric { border:1px solid var(--line); border-radius:12px; padding:16px; background:#fff; } .metric strong { display:block; font-size:25px; color:var(--accent); }
    label { display:block; color:var(--muted); font-size:13px; margin:10px 0 5px; } input, textarea, select { width:100%; border:1px solid #cbd6dc; border-radius:8px; padding:10px 11px; font:inherit; } textarea { min-height:86px; resize:vertical; }
    button { border:0; border-radius:8px; padding:10px 15px; background:var(--accent); color:white; font:inherit; cursor:pointer; } button.secondary { background:#edf2f4; color:var(--ink); } button:disabled { opacity:.5; cursor:not-allowed; }
    .row { display:flex; flex-wrap:wrap; gap:10px; align-items:center; } .split { display:grid; grid-template-columns:1fr 1fr; gap:14px; } @media(max-width:700px){.split{grid-template-columns:1fr;} header{display:block;} }
    nav { display:flex; flex-wrap:wrap; gap:6px; margin:0 0 18px; } nav button { background:#e9eff2; color:#29404f; } nav button.active { background:var(--accent); color:white; }
    .hidden { display:none !important; } .muted { color:var(--muted); } .notice { background:var(--warn); border-left:4px solid #d99b22; padding:10px 14px; border-radius:6px; }
    .tag { display:inline-block; background:var(--accent-2); color:#12636a; border-radius:999px; padding:2px 9px; font-size:12px; } .error { color:#a23a3a; white-space:pre-wrap; }
    pre { background:#102a43; color:#e5f1f5; padding:15px; border-radius:9px; overflow:auto; white-space:pre-wrap; }
    .timeline { border-left:2px solid #bfd2d8; margin:14px 0 0 8px; padding-left:18px; } .event { margin:0 0 14px; position:relative; } .event:before { content:""; position:absolute; width:9px; height:9px; background:var(--accent); border-radius:50%; left:-24px; top:8px; } .event small { color:var(--muted); }
    .status { font-weight:600; } .status.ok { color:#177e55; } .status.pending { color:#a36a12; }
  </style>
</head>
<body>
  <header><div><h1>研迹 ScholarTrace</h1><p>从研究问题、证据与实验到论文草稿的可追溯科研工作台</p></div><div id="header-status" class="tag">未连接项目</div></header>
  <main>
    <section id="start" class="panel">
      <h2>建立农业视觉研究工作区</h2><p class="muted">这是合成/脱敏演示入口。正式 Claim 仍必须绑定可核验来源。</p>
      <form id="project-form"><div class="split"><div><label>项目 ID</label><input id="project-id" value="lychee-vision-demo" pattern="[A-Za-z0-9._-]+" required></div><div><label>Thread ID</label><input id="thread-id" value="thread-lychee-vision-demo" required></div></div>
      <label>研究问题</label><textarea id="problem">如何在荔枝果园图像中稳定识别病虫害并保持评估结果可追溯？</textarea><label>当前目标</label><input id="goal" value="定义可检验的农业视觉研究问题"><div class="row" style="margin-top:14px"><button>创建/打开工作区</button><span id="start-error" class="error"></span></div></form>
    </section>
    <section id="workspace" class="hidden">
      <nav><button data-tab="overview" class="active">总览</button><button data-tab="question">研究问题</button><button data-tab="literature">文献与证据</button><button data-tab="experiments">实验与 Run</button><button data-tab="manuscript">论文草稿</button><button data-tab="figures">图表</button></nav>
      <div id="overview" class="tab"><section class="panel"><div class="row"><div><h2 id="project-title" style="margin:0"></h2><div id="project-meta" class="muted"></div></div><span id="project-stage" class="tag"></span><button id="refresh" class="secondary" style="margin-left:auto">刷新状态</button></div></section><section class="grid" id="counts"></section><section class="panel"><h3>工作台边界</h3><p class="notice">合成/脱敏数据只用于演示状态流和追溯协议；没有来源的 Claim 会保留为待验证，不会被页面自动升级。</p></section></div>
      <div id="question" class="tab hidden"><section class="panel"><h2>研究问题</h2><div id="question-list" class="muted">尚未保存研究问题。</div></section></div>
      <div id="literature" class="tab hidden"><section class="panel"><h2>文献与证据</h2><div class="grid"><div class="metric"><strong id="documents-count">0</strong>已批准文献</div><div class="metric"><strong id="evidence-count">0</strong>EvidenceCard</div></div><p class="muted">只有明确批准的项目文献才会进入证据链。</p></section></div>
      <div id="experiments" class="tab hidden"><section class="panel"><h2>实验与 Run 时间线</h2><div id="runs-list" class="muted">暂无受控 Run。</div><div id="timeline" class="timeline"></div></section></div>
      <div id="manuscript" class="tab hidden"><section class="panel"><div class="row"><div><h2>论文草稿</h2><p class="muted">确定性模板保留 Claim、MetricResult 和 citation 来源标记。</p></div><button id="create-manuscript" style="margin-left:auto">生成论文草稿契约</button><button id="submit-review" class="secondary" disabled>提交人工审阅</button></div><div id="manuscript-state" class="muted">尚未创建 Manuscript。</div><div id="draft-sections"></div></section></div>
      <div id="figures" class="tab hidden"><section class="panel"><h2>图表与 Artifact</h2><div id="figures-list" class="muted">暂无图表。</div></section></div>
    </section>
  </main>
  <script>
    const state = { projectId: null, manuscript: null, timelineEvents: new Map(), eventSources: new Map() };
    const $ = (id) => document.getElementById(id);
    function escapeHTML(value) { return String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;'); }
    async function request(path, options = {}) { const response = await fetch(path, { headers: {'Content-Type':'application/json'}, ...options }); const body = await response.json().catch(() => ({})); if (!response.ok) throw new Error(body.detail || ('HTTP ' + response.status)); return body; }
    function showTab(name) { document.querySelectorAll('.tab').forEach((node) => node.classList.toggle('hidden', node.id !== name)); document.querySelectorAll('nav button').forEach((node) => node.classList.toggle('active', node.dataset.tab === name)); }
    function renderCounts(data) { $('counts').innerHTML = [['questions','研究问题',data.questions.length],['documents','批准文献',data.documents.length],['evidence','证据卡',data.evidence.length],['runs','受控 Run',data.runs.length],['manuscripts','论文版本',data.manuscripts.length],['figures','图表',data.figures.length]].map(([_,label,value]) => `<div class="metric"><strong>${value}</strong>${label}</div>`).join(''); }
    function renderQuestion(items) { $('question-list').innerHTML = items.length ? items.map((item) => `<div class="panel"><span class="tag">v${escapeHTML(item.version)} · ${escapeHTML(item.status)}</span><p><b>${escapeHTML(item.question.problem)}</b></p><p class="muted">目标域：${escapeHTML(item.question.target_population_or_domain)}<br>成功标准：${escapeHTML(item.question.success_criteria.join('；'))}</p></div>`).join('') : '尚未保存研究问题。'; }
    function renderRuns(runs) { $('runs-list').innerHTML = runs.length ? runs.map((run) => `<div class="panel"><span class="tag">${escapeHTML(run.status)}</span> <b>${escapeHTML(run.execution_id)}</b><span class="muted"> · ${escapeHTML(run.backend)} · ${escapeHTML(run.plan_id)}</span></div>`).join('') : '暂无受控 Run。'; }
    function renderTimeline() {
      const events = [...state.timelineEvents.values()].sort((left, right) => left.created_at.localeCompare(right.created_at) || left.sequence - right.sequence);
      $('timeline').innerHTML = events.length ? events.map((event) => `<div class="event"><b>${escapeHTML(event.execution_id)}</b> <span class="tag">${escapeHTML(event.stream)}</span><div>${escapeHTML(event.message)}</div><small>#${escapeHTML(event.sequence)} · ${escapeHTML(event.created_at)}</small></div>`).join('') : '<span class="muted">暂无 Run 事件。</span>';
    }
    function consumeRunEvent(event) {
      try {
        const payload = JSON.parse(event.data);
        state.timelineEvents.set(`${payload.execution_id}:${payload.sequence}`, payload);
        renderTimeline();
      } catch (error) {
        $('timeline').innerHTML = `<span class="error">无法解析 Run 事件：${escapeHTML(error.message)}</span>`;
      }
    }
    function openRunStream(run) {
      const previous = state.eventSources.get(run.execution_id);
      if (previous) previous.close();
      const known = [...state.timelineEvents.values()].filter((event) => event.execution_id === run.execution_id);
      const after = known.reduce((latest, event) => Math.max(latest, event.sequence), -1);
      const source = new EventSource(`/api/projects/${encodeURIComponent(state.projectId)}/runs/${encodeURIComponent(run.execution_id)}/events/stream?after_sequence=${after}&live=true`);
      ['stdout', 'stderr', 'system'].forEach((stream) => source.addEventListener(stream, consumeRunEvent));
      source.onerror = () => {
        // EventSource retries with Last-Event-ID; keep the connection open so
        // a transient disconnect does not lose later Run events.
        if (source.readyState === EventSource.CLOSED) state.eventSources.delete(run.execution_id);
      };
      state.eventSources.set(run.execution_id, source);
    }
    async function refreshTimeline(runs) {
      state.eventSources.forEach((source) => source.close());
      state.eventSources.clear();
      state.timelineEvents.clear();
      for (const run of runs) {
        try {
          const events = await request(`/api/projects/${encodeURIComponent(state.projectId)}/runs/${encodeURIComponent(run.execution_id)}/events`);
          events.forEach((event) => state.timelineEvents.set(`${event.execution_id}:${event.sequence}`, event));
        } catch (error) {
          $('timeline').innerHTML = `<span class="error">无法加载 ${escapeHTML(run.execution_id)} 的事件：${escapeHTML(error.message)}</span>`;
        }
      }
      renderTimeline();
      runs.forEach(openRunStream);
    }
    function renderDraft(draft) { $('manuscript-state').innerHTML = `<span class="tag">${escapeHTML(state.manuscript.status)}</span> <b>${escapeHTML(state.manuscript.title)}</b>`; $('submit-review').disabled = state.manuscript.status !== 'draft'; $('draft-sections').innerHTML = draft.errors.map((error) => `<p class="error">${escapeHTML(error)}</p>`).join('') + draft.sections.map((section) => `<article class="panel"><h3>${escapeHTML(section.section_id)}</h3><pre>${escapeHTML(section.markdown)}</pre></article>`).join(''); }
    async function refresh() { if (!state.projectId) return; try { const id = encodeURIComponent(state.projectId); const [project,questions,documents,evidence,runs,manuscripts,figures] = await Promise.all([request(`/api/projects/${id}`),request(`/api/projects/${id}/research-questions`),request(`/api/projects/${id}/documents`),request(`/api/projects/${id}/evidence`),request(`/api/projects/${id}/runs`),request(`/api/projects/${id}/manuscripts`),request(`/api/projects/${id}/figures`)]); $('project-title').textContent = project.project_id; $('project-meta').textContent = project.current_goal || ''; $('project-stage').textContent = project.active_stage; renderQuestion(questions); renderRuns(runs); void refreshTimeline(runs); $('documents-count').textContent = documents.length; $('evidence-count').textContent = evidence.length; $('figures-list').textContent = figures.length ? `${figures.length} 个 FigureSpec 已保存` : '暂无图表。'; renderCounts({questions,documents,evidence,runs,manuscripts,figures}); if (manuscripts.length) { state.manuscript = manuscripts[manuscripts.length-1]; const draft = await request(`/api/projects/${id}/manuscripts/${state.manuscript.manuscript_id}/draft`); renderDraft(draft); } } catch (error) { $('start-error').textContent = error.message; } }
    $('project-form').addEventListener('submit', async (event) => { event.preventDefault(); $('start-error').textContent = ''; try { state.projectId = $('project-id').value; await request('/api/projects', {method:'POST',body:JSON.stringify({project_id:state.projectId,thread_id:$('thread-id').value,current_goal:$('goal').value})}); await request(`/api/projects/${encodeURIComponent(state.projectId)}/research-questions`, {method:'POST',body:JSON.stringify({problem:$('problem').value,target_population_or_domain:'荔枝果园农业视觉图像',inputs:['田间图像'],expected_outputs:['病虫害类别与定位'],constraints:['保留数据版本和采集协议'],success_criteria:['验证集指标可独立重算'],assumptions:['Fixture 仅用于离线演示'],unresolved_questions:['真实场景采集伦理待确认']})}); $('start').classList.add('hidden'); $('workspace').classList.remove('hidden'); $('header-status').textContent = state.projectId; await refresh(); } catch (error) { $('start-error').textContent = error.message; } });
    $('refresh').addEventListener('click', refresh); $('create-manuscript').addEventListener('click', async () => { try { await request(`/api/projects/${encodeURIComponent(state.projectId)}/manuscripts`, {method:'POST',body:JSON.stringify({title:'荔枝果园病虫害视觉研究草稿',target_template:'journal_article'})}); await refresh(); showTab('manuscript'); } catch (error) { $('manuscript-state').textContent = error.message; } }); $('submit-review').addEventListener('click', async () => { try { await request(`/api/projects/${encodeURIComponent(state.projectId)}/manuscripts/${state.manuscript.manuscript_id}/review`, {method:'POST',body:JSON.stringify({actor_id:'workbench-user',reason:'从工作台提交人工审阅'})}); await refresh(); } catch (error) { $('manuscript-state').textContent = error.message; } }); document.querySelectorAll('nav button').forEach((button) => button.addEventListener('click', () => showTab(button.dataset.tab)));
    const initialProject = new URLSearchParams(location.search).get('project'); if (initialProject) { state.projectId = initialProject; $('project-id').value = initialProject; $('start').classList.add('hidden'); $('workspace').classList.remove('hidden'); $('header-status').textContent = initialProject; refresh(); }
  </script>
</body>
</html>"""
