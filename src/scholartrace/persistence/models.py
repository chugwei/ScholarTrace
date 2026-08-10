"""SQLAlchemy models owned by the project repository."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now_naive() -> datetime:
    """Return UTC without tzinfo for stable SQLite round trips."""

    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class ProjectRow(Base):
    __tablename__ = "projects"

    project_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    thread_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    active_stage: Mapped[str] = mapped_column(String(64), nullable=False, default="intake")
    current_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now_naive,
        onupdate=utc_now_naive,
    )


class ResearchQuestionRow(Base):
    __tablename__ = "research_questions"
    __table_args__ = (
        UniqueConstraint("project_id", "version", name="uq_research_question_project_version"),
        UniqueConstraint(
            "project_id",
            "content_sha256",
            name="uq_research_question_project_content",
        ),
    )

    research_question_id: Mapped[str] = mapped_column(String(35), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    frozen_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    parent_research_question_id: Mapped[str | None] = mapped_column(
        String(35),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class DecisionRecordRow(Base):
    __tablename__ = "decision_records"
    __table_args__ = (UniqueConstraint("project_id", "decision_id", name="uq_decision_project_id"),)

    decision_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    thread_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class DocumentRow(Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("content_sha256", name="uq_document_content_sha256"),)

    document_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    ingest_status: Mapped[str] = mapped_column(String(24), nullable=False)
    quality_status: Mapped[str] = mapped_column(String(32), nullable=False)
    searchable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    authors: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    doi: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    storage_relpath: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_relpath: Mapped[str | None] = mapped_column(Text, nullable=True)
    parser_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class ProjectDocumentRow(Base):
    __tablename__ = "project_documents"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "document_id",
            name="uq_project_document_project_document",
        ),
    )

    project_document_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="candidate")
    relevance_score: Mapped[float | None] = mapped_column(nullable=True)
    relevance_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class DocumentChunkRow(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "ordinal", name="uq_document_chunk_document_ordinal"),
    )

    chunk_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class EvidenceCardRow(Base):
    __tablename__ = "evidence_cards"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "chunk_id",
            "source_start_offset",
            "source_end_offset",
            name="uq_evidence_card_project_span",
        ),
    )

    evidence_card_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("document_chunks.chunk_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    source_start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    source_end_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    locator_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    locator_value: Mapped[str] = mapped_column(Text, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(16), nullable=False)
    verified_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class PipelineSpecRow(Base):
    __tablename__ = "pipeline_specs"
    __table_args__ = (
        UniqueConstraint("project_id", "version", name="uq_pipeline_project_version"),
        UniqueConstraint("project_id", "content_sha256", name="uq_pipeline_project_content"),
    )

    pipeline_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    parent_pipeline_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class DataCollectionProtocolRow(Base):
    __tablename__ = "data_collection_protocols"
    __table_args__ = (
        UniqueConstraint("project_id", "version", name="uq_protocol_project_version"),
        UniqueConstraint("project_id", "content_sha256", name="uq_protocol_project_content"),
    )

    protocol_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    parent_protocol_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class AlgorithmSpecRow(Base):
    __tablename__ = "algorithm_specs"
    __table_args__ = (
        UniqueConstraint("project_id", "version", name="uq_algorithm_project_version"),
        UniqueConstraint("project_id", "content_sha256", name="uq_algorithm_project_content"),
    )

    algorithm_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    parent_algorithm_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class PriorArtMapRow(Base):
    __tablename__ = "prior_art_maps"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "algorithm_id",
            "version",
            name="uq_prior_art_map_version",
        ),
        UniqueConstraint("project_id", "content_sha256", name="uq_prior_art_map_content"),
    )

    map_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    algorithm_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("algorithm_specs.algorithm_id"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    parent_map_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class InnovationCandidateRow(Base):
    __tablename__ = "innovation_candidates"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "algorithm_id",
            "version",
            name="uq_innovation_candidate_version",
        ),
        UniqueConstraint("project_id", "content_sha256", name="uq_innovation_candidate_content"),
    )

    candidate_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    algorithm_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("algorithm_specs.algorithm_id"),
        nullable=False,
        index=True,
    )
    prior_art_map_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("prior_art_maps.map_id"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    parent_candidate_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class ExperimentPlanRow(Base):
    __tablename__ = "experiment_plans"
    __table_args__ = (
        UniqueConstraint("project_id", "version", name="uq_experiment_plan_version"),
        UniqueConstraint("project_id", "content_sha256", name="uq_experiment_plan_content"),
    )

    plan_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    algorithm_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("algorithm_specs.algorithm_id"), nullable=False, index=True
    )
    candidate_id: Mapped[str | None] = mapped_column(
        String(40), ForeignKey("innovation_candidates.candidate_id"), nullable=True, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    parent_plan_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class RunManifestRow(Base):
    __tablename__ = "run_manifests"

    run_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("experiment_plans.plan_id"), nullable=False, index=True
    )
    matrix_entry_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class MetricResultRow(Base):
    __tablename__ = "metric_results"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "name",
            "split",
            "source",
            name="uq_metric_run_name_split_source",
        ),
    )

    metric_result_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("run_manifests.run_id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    split: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[float] = mapped_column(nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class ClaimUpdateRow(Base):
    __tablename__ = "claim_updates"

    update_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    claim_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    metric_result_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    run_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class ControlledRunRow(Base):
    """A controlled execution request and its append-only lifecycle fields."""

    __tablename__ = "controlled_runs"

    execution_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("experiment_plans.plan_id"), nullable=False, index=True
    )
    matrix_entry_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    backend: Mapped[str] = mapped_column(String(16), nullable=False)
    command_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    log_relpath: Mapped[str | None] = mapped_column(Text, nullable=True)
    staging_relpath: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_relpath: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ControlledRunEventRow(Base):
    """Append-only event stream for controlled-run logs and state changes."""

    __tablename__ = "controlled_run_events"
    __table_args__ = (
        UniqueConstraint(
            "execution_id",
            "sequence",
            name="uq_controlled_run_event_sequence",
        ),
    )

    event_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    execution_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("controlled_runs.execution_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    stream: Mapped[str] = mapped_column(String(16), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class DebugCaseRow(Base):
    """Persisted failure evidence and gated repair lifecycle."""

    __tablename__ = "debug_cases"
    __table_args__ = (
        UniqueConstraint("project_id", "execution_id", name="uq_debug_case_project_execution"),
    )

    case_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    execution_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("controlled_runs.execution_id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(24), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class FigureSpecRow(Base):
    """Versioned figure design and provenance references."""

    __tablename__ = "figure_specs"
    __table_args__ = (
        UniqueConstraint("project_id", "content_sha256", name="uq_figure_project_content"),
    )

    figure_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class ManuscriptRow(Base):
    """Versioned manuscript container without generated section text."""

    __tablename__ = "manuscripts"
    __table_args__ = (
        UniqueConstraint("project_id", "version", name="uq_manuscript_project_version"),
        UniqueConstraint("project_id", "content_sha256", name="uq_manuscript_project_content"),
    )

    manuscript_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    parent_manuscript_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class SectionContractRow(Base):
    """Required sources and claims for one manuscript section."""

    __tablename__ = "section_contracts"
    __table_args__ = (
        UniqueConstraint(
            "manuscript_id",
            "section",
            name="uq_section_contract_manuscript_section",
        ),
    )

    section_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    manuscript_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("manuscripts.manuscript_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section: Mapped[str] = mapped_column(String(32), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class ClaimLedgerRow(Base):
    """Evidence-bound claim ledger entry."""

    __tablename__ = "claim_ledger"
    __table_args__ = (
        UniqueConstraint("project_id", "content_sha256", name="uq_claim_project_content"),
    )

    claim_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)
