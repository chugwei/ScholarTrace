"""Persistence and evidence gates for manuscript contracts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from scholartrace.identifiers import validate_identifier
from scholartrace.persistence.database import create_sqlite_engine
from scholartrace.persistence.models import (
    ClaimLedgerRow,
    EvidenceCardRow,
    ManuscriptRow,
    MetricResultRow,
    ProjectRow,
    RunManifestRow,
    SectionContractRow,
)
from scholartrace.schemas import Claim, Manuscript, SectionContract


class ManuscriptRepositoryError(RuntimeError):
    """Base error for manuscript persistence."""


class ManuscriptNotFoundError(ManuscriptRepositoryError):
    """Raised when a manuscript or section is absent from the requested project."""


class ManuscriptVersionConflictError(ManuscriptRepositoryError):
    """Raised when manuscript version history would be overwritten or skipped."""


class ManuscriptContractConflictError(ManuscriptRepositoryError):
    """Raised when a section contract conflicts with an existing contract."""


class ClaimLedgerConflictError(ManuscriptRepositoryError):
    """Raised when a claim identity or canonical content conflicts."""


class ClaimEvidenceError(ManuscriptRepositoryError):
    """Raised when a claim cannot be traced to project-scoped evidence."""


class ManuscriptRepository:
    """Persist versioned manuscript contracts without generating unsupported prose."""

    def __init__(self, database_path: Path) -> None:
        self._engine = create_sqlite_engine(database_path)

    def close(self) -> None:
        self._engine.dispose()

    def save_manuscript(self, manuscript: Manuscript) -> Manuscript:
        if manuscript.status != "draft":
            raise ValueError("new manuscripts must start as draft")
        manuscript_id = _required_identifier(manuscript.manuscript_id, "manuscript_id")
        project_id = _required_identifier(manuscript.project_id, "project_id")
        created_by = _required_identifier(manuscript.created_by, "created_by")
        digest = manuscript_content_sha256(manuscript)
        if manuscript.content_sha256 is not None and manuscript.content_sha256 != digest:
            raise ValueError("manuscript content_sha256 does not match the canonical payload")
        normalized = manuscript.model_copy(
            update={
                "manuscript_id": manuscript_id,
                "project_id": project_id,
                "content_sha256": digest,
                "created_by": created_by,
            }
        )
        with Session(self._engine) as session, session.begin():
            self._require_project(session, project_id)
            existing_content = session.scalar(
                select(ManuscriptRow).where(
                    ManuscriptRow.project_id == project_id,
                    ManuscriptRow.content_sha256 == digest,
                )
            )
            if existing_content is not None:
                return _manuscript_model(existing_content)
            if session.get(ManuscriptRow, manuscript_id) is not None:
                raise ManuscriptVersionConflictError(
                    f"manuscript_id {manuscript_id!r} is already persisted"
                )
            latest = session.scalar(
                select(ManuscriptRow)
                .where(ManuscriptRow.project_id == project_id)
                .order_by(ManuscriptRow.version.desc())
            )
            _validate_new_version(normalized, latest)
            row = ManuscriptRow(
                manuscript_id=manuscript_id,
                project_id=project_id,
                version=normalized.version,
                content_sha256=digest,
                payload=normalized.model_dump(mode="json"),
                status="draft",
                parent_manuscript_id=normalized.parent_manuscript_id,
                created_by=created_by,
                created_at=normalized.created_at.replace(tzinfo=None),
            )
            session.add(row)
            try:
                session.flush()
            except IntegrityError as error:
                raise ManuscriptVersionConflictError(
                    "manuscript version or content is already persisted"
                ) from error
            return _manuscript_model(row)

    def get_manuscript(self, project_id: str, manuscript_id: str) -> Manuscript:
        project_id = validate_identifier(project_id)
        manuscript_id = validate_identifier(manuscript_id)
        with Session(self._engine) as session:
            row = session.scalar(
                select(ManuscriptRow).where(
                    ManuscriptRow.project_id == project_id,
                    ManuscriptRow.manuscript_id == manuscript_id,
                )
            )
            if row is None:
                raise ManuscriptNotFoundError(
                    f"manuscript {manuscript_id!r} was not found in project {project_id!r}"
                )
            return _manuscript_model(row)

    def list_manuscripts(self, project_id: str) -> list[Manuscript]:
        project_id = validate_identifier(project_id)
        with Session(self._engine) as session:
            self._require_project(session, project_id)
            rows = session.scalars(
                select(ManuscriptRow)
                .where(ManuscriptRow.project_id == project_id)
                .order_by(ManuscriptRow.version)
            ).all()
            return [_manuscript_model(row) for row in rows]

    def save_section_contract(self, contract: SectionContract) -> SectionContract:
        if contract.status != "draft":
            raise ValueError("new section contracts must start as draft")
        section_id = _required_identifier(contract.section_id, "section_id")
        manuscript_id = _required_identifier(contract.manuscript_id, "manuscript_id")
        created_by = _required_identifier(contract.created_by, "created_by")
        digest = section_contract_content_sha256(contract)
        if contract.content_sha256 is not None and contract.content_sha256 != digest:
            raise ValueError("section contract content_sha256 does not match the canonical payload")
        normalized = contract.model_copy(
            update={
                "section_id": section_id,
                "manuscript_id": manuscript_id,
                "content_sha256": digest,
                "created_by": created_by,
            }
        )
        with Session(self._engine) as session, session.begin():
            manuscript = session.get(ManuscriptRow, manuscript_id)
            if manuscript is None:
                raise ManuscriptNotFoundError(f"manuscript {manuscript_id!r} was not found")
            existing_content = session.scalar(
                select(SectionContractRow).where(
                    SectionContractRow.manuscript_id == manuscript_id,
                    SectionContractRow.content_sha256 == digest,
                )
            )
            if existing_content is not None:
                return _section_contract_model(existing_content)
            if session.get(SectionContractRow, section_id) is not None:
                raise ManuscriptContractConflictError(
                    f"section_id {section_id!r} is already persisted"
                )
            row = SectionContractRow(
                section_id=section_id,
                manuscript_id=manuscript_id,
                section=normalized.section,
                content_sha256=digest,
                payload=normalized.model_dump(mode="json"),
                status="draft",
                created_by=created_by,
                created_at=normalized.created_at.replace(tzinfo=None),
            )
            session.add(row)
            manuscript_payload = dict(manuscript.payload)
            section_ids = list(manuscript_payload.get("section_ids", []))
            if section_id not in section_ids:
                manuscript_payload["section_ids"] = [*section_ids, section_id]
                manuscript.payload = manuscript_payload
            try:
                session.flush()
            except IntegrityError as error:
                raise ManuscriptContractConflictError(
                    "a section contract for this manuscript section is already persisted"
                ) from error
            return _section_contract_model(row)

    def get_section_contract(self, manuscript_id: str, section_id: str) -> SectionContract:
        manuscript_id = validate_identifier(manuscript_id)
        section_id = validate_identifier(section_id)
        with Session(self._engine) as session:
            row = session.scalar(
                select(SectionContractRow).where(
                    SectionContractRow.manuscript_id == manuscript_id,
                    SectionContractRow.section_id == section_id,
                )
            )
            if row is None:
                raise ManuscriptNotFoundError(
                    f"section contract {section_id!r} was not found for "
                    f"manuscript {manuscript_id!r}"
                )
            return _section_contract_model(row)

    def list_section_contracts(self, manuscript_id: str) -> list[SectionContract]:
        manuscript_id = validate_identifier(manuscript_id)
        with Session(self._engine) as session:
            rows = session.scalars(
                select(SectionContractRow)
                .where(SectionContractRow.manuscript_id == manuscript_id)
                .order_by(SectionContractRow.section)
            ).all()
            return [_section_contract_model(row) for row in rows]

    def save_claim(self, claim: Claim) -> Claim:
        claim_id = _required_identifier(claim.claim_id, "claim_id")
        project_id = _required_identifier(claim.project_id, "project_id")
        created_by = _required_identifier(claim.created_by, "created_by")
        digest = claim_content_sha256(claim)
        if claim.content_sha256 is not None and claim.content_sha256 != digest:
            raise ValueError("claim content_sha256 does not match the canonical payload")
        normalized = claim.model_copy(
            update={
                "claim_id": claim_id,
                "project_id": project_id,
                "content_sha256": digest,
                "created_by": created_by,
            }
        )
        with Session(self._engine) as session, session.begin():
            self._require_project(session, project_id)
            self._validate_claim_evidence(session, normalized)
            existing_content = session.scalar(
                select(ClaimLedgerRow).where(
                    ClaimLedgerRow.project_id == project_id,
                    ClaimLedgerRow.content_sha256 == digest,
                )
            )
            if existing_content is not None:
                return _claim_model(existing_content)
            if session.get(ClaimLedgerRow, claim_id) is not None:
                raise ClaimLedgerConflictError(f"claim_id {claim_id!r} is already persisted")
            row = ClaimLedgerRow(
                claim_id=claim_id,
                project_id=project_id,
                content_sha256=digest,
                payload=normalized.model_dump(mode="json"),
                claim_type=normalized.claim_type,
                status=normalized.status,
                created_by=created_by,
                created_at=normalized.created_at.replace(tzinfo=None),
            )
            session.add(row)
            try:
                session.flush()
            except IntegrityError as error:
                raise ClaimLedgerConflictError(
                    "claim identity or canonical content is already persisted"
                ) from error
            return _claim_model(row)

    def get_claim(self, project_id: str, claim_id: str) -> Claim:
        project_id = validate_identifier(project_id)
        claim_id = validate_identifier(claim_id)
        with Session(self._engine) as session:
            row = session.scalar(
                select(ClaimLedgerRow).where(
                    ClaimLedgerRow.project_id == project_id,
                    ClaimLedgerRow.claim_id == claim_id,
                )
            )
            if row is None:
                raise ManuscriptNotFoundError(
                    f"claim {claim_id!r} was not found in project {project_id!r}"
                )
            return _claim_model(row)

    def list_claims(self, project_id: str) -> list[Claim]:
        project_id = validate_identifier(project_id)
        with Session(self._engine) as session:
            self._require_project(session, project_id)
            rows = session.scalars(
                select(ClaimLedgerRow)
                .where(ClaimLedgerRow.project_id == project_id)
                .order_by(ClaimLedgerRow.created_at, ClaimLedgerRow.claim_id)
            ).all()
            return [_claim_model(row) for row in rows]

    @staticmethod
    def _require_project(session: Session, project_id: str) -> None:
        if session.get(ProjectRow, project_id) is None:
            raise ManuscriptRepositoryError(f"project {project_id!r} was not found")

    @staticmethod
    def _validate_claim_evidence(session: Session, claim: Claim) -> None:
        project_id = _required_identifier(claim.project_id, "project_id")
        if claim.evidence_ids:
            evidence_rows = session.scalars(
                select(EvidenceCardRow).where(
                    EvidenceCardRow.project_id == project_id,
                    EvidenceCardRow.evidence_card_id.in_(claim.evidence_ids),
                )
            ).all()
            if len(evidence_rows) != len(set(claim.evidence_ids)):
                raise ClaimEvidenceError("claim references missing project evidence cards")
            if claim.status == "supported" and any(
                row.verification_status != "verified" for row in evidence_rows
            ):
                raise ClaimEvidenceError("supported claims require verified evidence cards")
        if claim.experiment_run_ids:
            run_rows = session.scalars(
                select(RunManifestRow).where(
                    RunManifestRow.project_id == project_id,
                    RunManifestRow.run_id.in_(claim.experiment_run_ids),
                )
            ).all()
            if len(run_rows) != len(set(claim.experiment_run_ids)):
                raise ClaimEvidenceError("claim references missing project runs")
            if claim.status == "supported" and any(row.status != "validated" for row in run_rows):
                raise ClaimEvidenceError("supported claims require validated runs")
        if claim.metric_result_ids:
            metric_rows = session.scalars(
                select(MetricResultRow).where(
                    MetricResultRow.project_id == project_id,
                    MetricResultRow.metric_result_id.in_(claim.metric_result_ids),
                )
            ).all()
            if len(metric_rows) != len(set(claim.metric_result_ids)):
                raise ClaimEvidenceError("claim references missing project metrics")
            if claim.status == "supported" and any(
                row.verification_status != "verified" or not row.is_final for row in metric_rows
            ):
                raise ClaimEvidenceError("supported claims require verified final metrics")


def _required_identifier(value: str | None, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} is required for persistence")
    return validate_identifier(value)


def _canonical_sha256(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def manuscript_content_sha256(manuscript: Manuscript) -> str:
    return _canonical_sha256(
        manuscript.model_dump(
            mode="json",
            exclude={
                "manuscript_id",
                "project_id",
                "version",
                "parent_manuscript_id",
                "status",
                "content_sha256",
                "created_by",
                "created_at",
            },
        )
    )


def section_contract_content_sha256(contract: SectionContract) -> str:
    return _canonical_sha256(
        contract.model_dump(
            mode="json",
            exclude={
                "section_id",
                "manuscript_id",
                "status",
                "content_sha256",
                "created_by",
                "created_at",
            },
        )
    )


def claim_content_sha256(claim: Claim) -> str:
    return _canonical_sha256(
        claim.model_dump(
            mode="json",
            exclude={
                "claim_id",
                "project_id",
                "status",
                "content_sha256",
                "created_by",
                "created_at",
            },
        )
    )


def _validate_new_version(manuscript: Manuscript, latest: ManuscriptRow | None) -> None:
    if latest is None:
        if manuscript.version != 1 or manuscript.parent_manuscript_id is not None:
            raise ManuscriptVersionConflictError(
                "first manuscript version must be 1 without a parent"
            )
        return
    if manuscript.version != latest.version + 1:
        raise ManuscriptVersionConflictError("manuscript versions must increment by one")
    if manuscript.parent_manuscript_id != latest.manuscript_id:
        raise ManuscriptVersionConflictError(
            "new manuscript versions must name the latest manuscript as parent"
        )


def _manuscript_model(row: ManuscriptRow) -> Manuscript:
    payload = dict(row.payload)
    payload.update(
        {
            "manuscript_id": row.manuscript_id,
            "project_id": row.project_id,
            "version": row.version,
            "content_sha256": row.content_sha256,
            "status": row.status,
            "parent_manuscript_id": row.parent_manuscript_id,
            "created_by": row.created_by,
            "created_at": row.created_at,
        }
    )
    return Manuscript.model_validate(payload)


def _section_contract_model(row: SectionContractRow) -> SectionContract:
    payload = dict(row.payload)
    payload.update(
        {
            "section_id": row.section_id,
            "manuscript_id": row.manuscript_id,
            "content_sha256": row.content_sha256,
            "status": row.status,
            "created_by": row.created_by,
            "created_at": row.created_at,
        }
    )
    return SectionContract.model_validate(payload)


def _claim_model(row: ClaimLedgerRow) -> Claim:
    payload = dict(row.payload)
    payload.update(
        {
            "claim_id": row.claim_id,
            "project_id": row.project_id,
            "content_sha256": row.content_sha256,
            "status": row.status,
            "created_by": row.created_by,
            "created_at": row.created_at,
        }
    )
    return Claim.model_validate(payload)
