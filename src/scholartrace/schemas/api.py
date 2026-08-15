"""HTTP request/response contracts for the ScholarTrace workbench API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from scholartrace.schemas.manuscript import ManuscriptTemplate, SectionDraft
from scholartrace.schemas.research import IdentifierText, NonBlankText, ResearchQuestion


class ProjectCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: IdentifierText
    thread_id: IdentifierText
    current_goal: str | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: NonBlankText
    thread_id: NonBlankText
    active_stage: NonBlankText
    current_goal: str | None = None
    created_at: datetime
    updated_at: datetime


class ArtifactResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_id: NonBlankText
    project_id: NonBlankText
    status: NonBlankText
    log_relpath: str | None = None
    staging_relpath: str | None = None
    published_relpath: str | None = None


class ManuscriptCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: NonBlankText
    target_template: ManuscriptTemplate = "journal_article"


class ManuscriptDraftResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manuscript_id: NonBlankText
    sections: list[SectionDraft]
    errors: list[NonBlankText] = Field(default_factory=list)


class ManuscriptReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor_id: NonBlankText
    reason: NonBlankText


class LLMStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    provider: str | None = None
    model: str | None = None


class ResearchQuestionCandidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    problem: NonBlankText
    context: str | None = Field(default=None, max_length=8000)


class ResearchQuestionCandidateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["candidate"] = "candidate"
    candidate: ResearchQuestion
    provider: NonBlankText
    model: NonBlankText
    warnings: list[NonBlankText] = Field(default_factory=list)


class ProjectDocumentReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["approved", "rejected"]
    actor_id: IdentifierText
    reason: NonBlankText
    relevance_score: float | None = Field(default=None, ge=0, le=1)
