"""Transactional persistence for algorithm specs and prior-art maps."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from scholartrace.algorithm.ranking import rank_innovation_candidates
from scholartrace.algorithm.validation import (
    validate_algorithm_spec,
    validate_innovation_candidate,
    validate_prior_art_map,
)
from scholartrace.identifiers import validate_identifier
from scholartrace.persistence.database import create_sqlite_engine
from scholartrace.persistence.models import (
    AlgorithmSpecRow,
    EvidenceCardRow,
    InnovationCandidateRow,
    PriorArtMapRow,
    ProjectRow,
    utc_now_naive,
)
from scholartrace.schemas import (
    AlgorithmSpec,
    InnovationCandidate,
    InnovationCandidateRanking,
    PriorArtMap,
)


class AlgorithmRepositoryError(RuntimeError):
    """Base error for algorithm-design persistence."""


class AlgorithmNotFoundError(AlgorithmRepositoryError):
    """Raised when an algorithm spec is absent from a project."""


class PriorArtMapNotFoundError(AlgorithmRepositoryError):
    """Raised when a prior-art map is absent from a project."""


class AlgorithmVersionConflictError(AlgorithmRepositoryError):
    """Raised when a version would overwrite or skip algorithm history."""


class AlgorithmDecisionConflictError(AlgorithmRepositoryError):
    """Raised when an algorithm decision cannot be applied safely."""


class PriorArtDecisionConflictError(AlgorithmRepositoryError):
    """Raised when a prior-art decision cannot be applied safely."""


class InnovationCandidateConflictError(AlgorithmRepositoryError):
    """Raised when a candidate cannot be persisted with traceable references."""


class AlgorithmRepository:
    """Persist reviewable, versioned algorithm designs and evidence maps."""

    def __init__(self, database_path: Path) -> None:
        self._engine = create_sqlite_engine(database_path)

    def close(self) -> None:
        self._engine.dispose()

    def save_algorithm(self, spec: AlgorithmSpec) -> AlgorithmSpec:
        if spec.status != "draft":
            raise ValueError("new algorithm specifications must start as draft")
        project_id = validate_identifier(spec.project_id)
        content_sha256 = algorithm_content_sha256(spec)
        if spec.content_sha256 is not None and spec.content_sha256 != content_sha256:
            raise ValueError("algorithm content_sha256 does not match the canonical payload")
        normalized = spec.model_copy(update={"content_sha256": content_sha256})
        with Session(self._engine) as session, session.begin():
            self._require_project(session, project_id)
            existing = session.scalar(
                select(AlgorithmSpecRow).where(
                    AlgorithmSpecRow.project_id == project_id,
                    AlgorithmSpecRow.content_sha256 == content_sha256,
                )
            )
            if existing is not None:
                return _algorithm_model(existing)
            if session.get(AlgorithmSpecRow, normalized.algorithm_id) is not None:
                raise AlgorithmVersionConflictError(
                    f"algorithm_id {normalized.algorithm_id!r} is already persisted"
                )
            latest = session.scalar(
                select(AlgorithmSpecRow)
                .where(AlgorithmSpecRow.project_id == project_id)
                .order_by(AlgorithmSpecRow.version.desc())
            )
            self._validate_new_version(
                session,
                normalized.version,
                normalized.parent_algorithm_id,
                latest,
                "algorithm",
            )
            row = AlgorithmSpecRow(
                algorithm_id=normalized.algorithm_id,
                project_id=project_id,
                version=normalized.version,
                content_sha256=content_sha256,
                payload=normalized.model_dump(mode="json"),
                status="draft",
                parent_algorithm_id=normalized.parent_algorithm_id,
                created_by=normalized.created_by,
                decision_reason=normalized.decision_reason,
                created_at=normalized.created_at.replace(tzinfo=None),
            )
            session.add(row)
            self._flush_or_conflict(session, "algorithm version is already persisted")
            return _algorithm_model(row)

    def approve_algorithm(
        self, project_id: str, algorithm_id: str, actor_id: str, reason: str
    ) -> AlgorithmSpec:
        project_id = validate_identifier(project_id)
        algorithm_id = validate_identifier(algorithm_id)
        actor_id = validate_identifier(actor_id)
        if not reason.strip():
            raise ValueError("approval reason is required")
        with Session(self._engine) as session, session.begin():
            row = self._algorithm_for_update(session, project_id, algorithm_id)
            spec = _algorithm_model(row)
            report = validate_algorithm_spec(
                spec,
                available_evidence_ids=self._evidence_ids(session, project_id),
            )
            if not report.passed:
                raise AlgorithmDecisionConflictError(
                    "; ".join(finding.message for finding in report.findings)
                )
            self._approve_row(session, row, actor_id, reason)
            return _algorithm_model(row)

    def reject_algorithm(
        self, project_id: str, algorithm_id: str, actor_id: str, reason: str
    ) -> AlgorithmSpec:
        project_id = validate_identifier(project_id)
        algorithm_id = validate_identifier(algorithm_id)
        actor_id = validate_identifier(actor_id)
        if not reason.strip():
            raise ValueError("rejection reason is required")
        with Session(self._engine) as session, session.begin():
            row = self._algorithm_for_update(session, project_id, algorithm_id)
            if row.status != "draft":
                raise AlgorithmDecisionConflictError("only draft algorithms can be rejected")
            row.status = "rejected"
            row.decision_reason = f"{actor_id}: {reason.strip()}"
            session.flush()
            return _algorithm_model(row)

    def get_algorithm(self, project_id: str, algorithm_id: str) -> AlgorithmSpec:
        project_id = validate_identifier(project_id)
        algorithm_id = validate_identifier(algorithm_id)
        with Session(self._engine) as session:
            return _algorithm_model(self._algorithm_for_update(session, project_id, algorithm_id))

    def list_algorithms(self, project_id: str) -> list[AlgorithmSpec]:
        project_id = validate_identifier(project_id)
        with Session(self._engine) as session:
            self._require_project(session, project_id)
            rows = session.scalars(
                select(AlgorithmSpecRow)
                .where(AlgorithmSpecRow.project_id == project_id)
                .order_by(AlgorithmSpecRow.version)
            ).all()
            return [_algorithm_model(row) for row in rows]

    def save_prior_art_map(self, prior_art_map: PriorArtMap) -> PriorArtMap:
        if prior_art_map.status != "draft":
            raise ValueError("new prior-art maps must start as draft")
        project_id = validate_identifier(prior_art_map.project_id)
        content_sha256 = prior_art_map_content_sha256(prior_art_map)
        if (
            prior_art_map.content_sha256 is not None
            and prior_art_map.content_sha256 != content_sha256
        ):
            raise ValueError("prior-art map content_sha256 does not match the canonical payload")
        normalized = prior_art_map.model_copy(update={"content_sha256": content_sha256})
        with Session(self._engine) as session, session.begin():
            self._require_project(session, project_id)
            algorithm = session.get(AlgorithmSpecRow, normalized.algorithm_id)
            if algorithm is None or algorithm.project_id != project_id:
                raise AlgorithmRepositoryError(
                    f"algorithm {normalized.algorithm_id!r} was not found in project {project_id!r}"
                )
            existing = session.scalar(
                select(PriorArtMapRow).where(
                    PriorArtMapRow.project_id == project_id,
                    PriorArtMapRow.content_sha256 == content_sha256,
                )
            )
            if existing is not None:
                return _prior_art_map_model(existing)
            if session.get(PriorArtMapRow, normalized.map_id) is not None:
                raise AlgorithmVersionConflictError(
                    f"map_id {normalized.map_id!r} is already persisted"
                )
            latest = session.scalar(
                select(PriorArtMapRow)
                .where(
                    PriorArtMapRow.project_id == project_id,
                    PriorArtMapRow.algorithm_id == normalized.algorithm_id,
                )
                .order_by(PriorArtMapRow.version.desc())
            )
            self._validate_new_version(
                session,
                normalized.version,
                normalized.parent_map_id,
                latest,
                "prior-art map",
            )
            row = PriorArtMapRow(
                map_id=normalized.map_id,
                project_id=project_id,
                algorithm_id=normalized.algorithm_id,
                version=normalized.version,
                content_sha256=content_sha256,
                payload=normalized.model_dump(mode="json"),
                status="draft",
                parent_map_id=normalized.parent_map_id,
                created_by=normalized.created_by,
                decision_reason=normalized.decision_reason,
                created_at=normalized.created_at.replace(tzinfo=None),
            )
            session.add(row)
            self._flush_or_conflict(session, "prior-art map version is already persisted")
            return _prior_art_map_model(row)

    def approve_prior_art_map(
        self, project_id: str, map_id: str, actor_id: str, reason: str
    ) -> PriorArtMap:
        project_id = validate_identifier(project_id)
        map_id = validate_identifier(map_id)
        actor_id = validate_identifier(actor_id)
        if not reason.strip():
            raise ValueError("approval reason is required")
        with Session(self._engine) as session, session.begin():
            row = self._prior_art_map_for_update(session, project_id, map_id)
            algorithm = session.get(AlgorithmSpecRow, row.algorithm_id)
            if algorithm is None or algorithm.status != "approved":
                raise PriorArtDecisionConflictError(
                    "prior-art maps require an approved algorithm specification"
                )
            report = validate_prior_art_map(
                _prior_art_map_model(row),
                available_evidence_ids=self._evidence_ids(session, project_id),
            )
            if not report.passed:
                raise PriorArtDecisionConflictError(
                    "; ".join(finding.message for finding in report.findings)
                )
            if row.status == "approved":
                if row.approved_by != actor_id:
                    raise PriorArtDecisionConflictError("approved map belongs to another actor")
                return _prior_art_map_model(row)
            if row.status != "draft":
                raise PriorArtDecisionConflictError("only draft prior-art maps can be approved")
            siblings = session.scalars(
                select(PriorArtMapRow).where(
                    PriorArtMapRow.project_id == project_id,
                    PriorArtMapRow.algorithm_id == row.algorithm_id,
                    PriorArtMapRow.status == "approved",
                    PriorArtMapRow.version < row.version,
                )
            ).all()
            for sibling in siblings:
                sibling.status = "superseded"
            row.status = "approved"
            row.approved_by = actor_id
            row.approved_at = utc_now_naive()
            row.decision_reason = reason.strip()
            return _prior_art_map_model(row)

    def reject_prior_art_map(
        self, project_id: str, map_id: str, actor_id: str, reason: str
    ) -> PriorArtMap:
        project_id = validate_identifier(project_id)
        map_id = validate_identifier(map_id)
        actor_id = validate_identifier(actor_id)
        if not reason.strip():
            raise ValueError("rejection reason is required")
        with Session(self._engine) as session, session.begin():
            row = self._prior_art_map_for_update(session, project_id, map_id)
            if row.status != "draft":
                raise PriorArtDecisionConflictError("only draft prior-art maps can be rejected")
            row.status = "rejected"
            row.decision_reason = f"{actor_id}: {reason.strip()}"
            return _prior_art_map_model(row)

    def get_prior_art_map(self, project_id: str, map_id: str) -> PriorArtMap:
        project_id = validate_identifier(project_id)
        map_id = validate_identifier(map_id)
        with Session(self._engine) as session:
            return _prior_art_map_model(self._prior_art_map_for_update(session, project_id, map_id))

    def list_prior_art_maps(self, project_id: str, algorithm_id: str) -> list[PriorArtMap]:
        project_id = validate_identifier(project_id)
        algorithm_id = validate_identifier(algorithm_id)
        with Session(self._engine) as session:
            self._require_project(session, project_id)
            rows = session.scalars(
                select(PriorArtMapRow)
                .where(
                    PriorArtMapRow.project_id == project_id,
                    PriorArtMapRow.algorithm_id == algorithm_id,
                )
                .order_by(PriorArtMapRow.version)
            ).all()
            return [_prior_art_map_model(row) for row in rows]

    def save_candidate(self, candidate: InnovationCandidate) -> InnovationCandidate:
        """Persist a draft only after its map and evidence references are coherent."""

        if candidate.status != "draft":
            raise ValueError("new innovation candidates must start as draft")
        project_id = validate_identifier(candidate.project_id)
        content_sha256 = candidate_content_sha256(candidate)
        if candidate.content_sha256 is not None and candidate.content_sha256 != content_sha256:
            raise ValueError("candidate content_sha256 does not match the canonical payload")
        normalized = candidate.model_copy(update={"content_sha256": content_sha256})
        with Session(self._engine) as session, session.begin():
            self._require_project(session, project_id)
            algorithm = session.get(AlgorithmSpecRow, normalized.algorithm_id)
            prior_art_map = session.get(PriorArtMapRow, normalized.prior_art_map_id)
            if algorithm is None or algorithm.project_id != project_id:
                raise InnovationCandidateConflictError(
                    f"algorithm {normalized.algorithm_id!r} was not found in project {project_id!r}"
                )
            if (
                prior_art_map is None
                or prior_art_map.project_id != project_id
                or prior_art_map.algorithm_id != normalized.algorithm_id
            ):
                raise InnovationCandidateConflictError(
                    f"prior-art map {normalized.prior_art_map_id!r} does not match the candidate"
                )
            report = validate_innovation_candidate(
                normalized,
                _prior_art_map_model(prior_art_map),
                available_evidence_ids=self._evidence_ids(session, project_id),
            )
            if not report.passed:
                raise InnovationCandidateConflictError(
                    "; ".join(finding.message for finding in report.findings)
                )
            existing = session.scalar(
                select(InnovationCandidateRow).where(
                    InnovationCandidateRow.project_id == project_id,
                    InnovationCandidateRow.content_sha256 == content_sha256,
                )
            )
            if existing is not None:
                return _candidate_model(existing)
            if session.get(InnovationCandidateRow, normalized.candidate_id) is not None:
                raise InnovationCandidateConflictError(
                    f"candidate_id {normalized.candidate_id!r} is already persisted"
                )
            latest = session.scalar(
                select(InnovationCandidateRow)
                .where(
                    InnovationCandidateRow.project_id == project_id,
                    InnovationCandidateRow.algorithm_id == normalized.algorithm_id,
                )
                .order_by(InnovationCandidateRow.version.desc())
            )
            self._validate_new_version(
                session,
                normalized.version,
                normalized.parent_candidate_id,
                latest,
                "innovation candidate",
            )
            row = InnovationCandidateRow(
                candidate_id=normalized.candidate_id,
                project_id=project_id,
                algorithm_id=normalized.algorithm_id,
                prior_art_map_id=normalized.prior_art_map_id,
                version=normalized.version,
                content_sha256=content_sha256,
                payload=normalized.model_dump(mode="json"),
                status="draft",
                parent_candidate_id=normalized.parent_candidate_id,
                created_by=normalized.created_by,
                decision_reason=normalized.decision_reason,
                created_at=normalized.created_at.replace(tzinfo=None),
            )
            session.add(row)
            self._flush_or_conflict(session, "innovation candidate version is already persisted")
            return _candidate_model(row)

    def get_candidate(self, project_id: str, candidate_id: str) -> InnovationCandidate:
        project_id = validate_identifier(project_id)
        candidate_id = validate_identifier(candidate_id)
        with Session(self._engine) as session:
            return _candidate_model(self._candidate_for_update(session, project_id, candidate_id))

    def list_candidates(
        self, project_id: str, algorithm_id: str | None = None
    ) -> list[InnovationCandidate]:
        project_id = validate_identifier(project_id)
        with Session(self._engine) as session:
            self._require_project(session, project_id)
            statement = select(InnovationCandidateRow).where(
                InnovationCandidateRow.project_id == project_id
            )
            if algorithm_id is not None:
                statement = statement.where(
                    InnovationCandidateRow.algorithm_id == validate_identifier(algorithm_id)
                )
            rows = session.scalars(
                statement.order_by(
                    InnovationCandidateRow.version,
                    InnovationCandidateRow.candidate_id,
                )
            ).all()
            return [_candidate_model(row) for row in rows]

    def rank_candidates(
        self, project_id: str, algorithm_id: str | None = None
    ) -> list[InnovationCandidateRanking]:
        """Return deterministic completeness ranks, never a novelty verdict."""

        return rank_innovation_candidates(self.list_candidates(project_id, algorithm_id))

    @staticmethod
    def _require_project(session: Session, project_id: str) -> None:
        if session.get(ProjectRow, project_id) is None:
            raise AlgorithmRepositoryError(f"project {project_id!r} was not found")

    @staticmethod
    def _validate_new_version(
        session: Session,
        version: int,
        parent_id: str | None,
        latest: AlgorithmSpecRow | PriorArtMapRow | InnovationCandidateRow | None,
        label: str,
    ) -> None:
        if latest is None:
            if version != 1 or parent_id is not None:
                raise AlgorithmVersionConflictError(
                    f"first {label} version must be 1 without a parent"
                )
            return
        if version != latest.version + 1:
            raise AlgorithmVersionConflictError(f"{label} versions must increment by one")
        if isinstance(latest, AlgorithmSpecRow):
            latest_id = latest.algorithm_id
        elif isinstance(latest, PriorArtMapRow):
            latest_id = latest.map_id
        else:
            latest_id = latest.candidate_id
        if latest.status in {"approved", "superseded"}:
            if parent_id != latest_id:
                raise AlgorithmVersionConflictError(
                    f"new {label} versions must name the current approved parent"
                )
        elif parent_id is not None and session.get(type(latest), parent_id) is None:
            raise AlgorithmVersionConflictError(f"{label} parent was not found")

    @staticmethod
    def _flush_or_conflict(session: Session, message: str) -> None:
        try:
            session.flush()
        except IntegrityError as error:
            raise AlgorithmVersionConflictError(message) from error

    @staticmethod
    def _approve_row(session: Session, row: AlgorithmSpecRow, actor_id: str, reason: str) -> None:
        if row.status == "approved":
            if row.approved_by != actor_id:
                raise AlgorithmDecisionConflictError("approved algorithm belongs to another actor")
            return
        if row.status != "draft":
            raise AlgorithmDecisionConflictError("only draft algorithms can be approved")
        siblings = session.scalars(
            select(AlgorithmSpecRow).where(
                AlgorithmSpecRow.project_id == row.project_id,
                AlgorithmSpecRow.status == "approved",
                AlgorithmSpecRow.version < row.version,
            )
        ).all()
        for sibling in siblings:
            sibling.status = "superseded"
        row.status = "approved"
        row.approved_by = actor_id
        row.approved_at = utc_now_naive()
        row.decision_reason = reason.strip()

    @staticmethod
    def _algorithm_for_update(
        session: Session, project_id: str, algorithm_id: str
    ) -> AlgorithmSpecRow:
        row = session.scalar(
            select(AlgorithmSpecRow).where(
                AlgorithmSpecRow.project_id == project_id,
                AlgorithmSpecRow.algorithm_id == algorithm_id,
            )
        )
        if row is None:
            raise AlgorithmNotFoundError(
                f"algorithm {algorithm_id!r} was not found in project {project_id!r}"
            )
        return row

    @staticmethod
    def _prior_art_map_for_update(session: Session, project_id: str, map_id: str) -> PriorArtMapRow:
        row = session.scalar(
            select(PriorArtMapRow).where(
                PriorArtMapRow.project_id == project_id,
                PriorArtMapRow.map_id == map_id,
            )
        )
        if row is None:
            raise PriorArtMapNotFoundError(
                f"prior-art map {map_id!r} was not found in project {project_id!r}"
            )
        return row

    @staticmethod
    def _candidate_for_update(
        session: Session, project_id: str, candidate_id: str
    ) -> InnovationCandidateRow:
        row = session.scalar(
            select(InnovationCandidateRow).where(
                InnovationCandidateRow.project_id == project_id,
                InnovationCandidateRow.candidate_id == candidate_id,
            )
        )
        if row is None:
            raise InnovationCandidateConflictError(
                f"candidate {candidate_id!r} was not found in project {project_id!r}"
            )
        return row

    @staticmethod
    def _evidence_ids(session: Session, project_id: str) -> set[str]:
        return set(
            session.scalars(
                select(EvidenceCardRow.evidence_card_id).where(
                    EvidenceCardRow.project_id == project_id
                )
            ).all()
        )


def algorithm_content_sha256(spec: AlgorithmSpec) -> str:
    return _content_sha256(
        spec.model_dump(
            mode="json",
            exclude={
                "algorithm_id",
                "project_id",
                "version",
                "status",
                "content_sha256",
                "parent_algorithm_id",
                "created_by",
                "decision_reason",
                "approved_by",
                "approved_at",
                "created_at",
            },
        )
    )


def prior_art_map_content_sha256(prior_art_map: PriorArtMap) -> str:
    return _content_sha256(
        prior_art_map.model_dump(
            mode="json",
            exclude={
                "map_id",
                "project_id",
                "version",
                "status",
                "content_sha256",
                "parent_map_id",
                "created_by",
                "decision_reason",
                "approved_by",
                "approved_at",
                "created_at",
            },
        )
    )


def candidate_content_sha256(candidate: InnovationCandidate) -> str:
    return _content_sha256(
        candidate.model_dump(
            mode="json",
            exclude={
                "candidate_id",
                "project_id",
                "version",
                "status",
                "content_sha256",
                "parent_candidate_id",
                "created_by",
                "decision_reason",
                "approved_by",
                "approved_at",
                "created_at",
            },
        )
    )


def _content_sha256(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _algorithm_model(row: AlgorithmSpecRow) -> AlgorithmSpec:
    payload = dict(row.payload)
    payload.update(
        {
            "algorithm_id": row.algorithm_id,
            "project_id": row.project_id,
            "version": row.version,
            "content_sha256": row.content_sha256,
            "status": row.status,
            "parent_algorithm_id": row.parent_algorithm_id,
            "created_by": row.created_by,
            "decision_reason": row.decision_reason,
            "approved_by": row.approved_by,
            "approved_at": row.approved_at,
            "created_at": row.created_at,
        }
    )
    return AlgorithmSpec.model_validate(payload)


def _prior_art_map_model(row: PriorArtMapRow) -> PriorArtMap:
    payload = dict(row.payload)
    payload.update(
        {
            "map_id": row.map_id,
            "project_id": row.project_id,
            "algorithm_id": row.algorithm_id,
            "version": row.version,
            "content_sha256": row.content_sha256,
            "status": row.status,
            "parent_map_id": row.parent_map_id,
            "created_by": row.created_by,
            "decision_reason": row.decision_reason,
            "approved_by": row.approved_by,
            "approved_at": row.approved_at,
            "created_at": row.created_at,
        }
    )
    return PriorArtMap.model_validate(payload)


def _candidate_model(row: InnovationCandidateRow) -> InnovationCandidate:
    payload = dict(row.payload)
    payload.update(
        {
            "candidate_id": row.candidate_id,
            "project_id": row.project_id,
            "algorithm_id": row.algorithm_id,
            "prior_art_map_id": row.prior_art_map_id,
            "version": row.version,
            "content_sha256": row.content_sha256,
            "status": row.status,
            "parent_candidate_id": row.parent_candidate_id,
            "created_by": row.created_by,
            "decision_reason": row.decision_reason,
            "approved_by": row.approved_by,
            "approved_at": row.approved_at,
            "created_at": row.created_at,
        }
    )
    return InnovationCandidate.model_validate(payload)
