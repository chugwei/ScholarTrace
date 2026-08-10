from pathlib import Path

import pytest
from pydantic import ValidationError

from scholartrace.persistence.migrations import LATEST_REVISION, current_revision, upgrade_database
from scholartrace.persistence.repository import (
    DecisionConflictError,
    ProjectNotFoundError,
    ProjectRepository,
)
from scholartrace.schemas.decisions import DecisionRecord


def decision_kwargs(decision_id: str = "decision-001") -> dict[str, object]:
    return {
        "decision_id": decision_id,
        "project_id": "lychee-m2-decision",
        "thread_id": "lychee-m2-decision",
        "target_type": "research_question",
        "target_id": "rq_pending-001",
        "action": "approved",
        "actor_id": "researcher-001",
        "reason": "已确认研究问题边界和数据授权前提",
        "payload": {"source": "human-review"},
        "created_at": "2026-08-10T12:00:00Z",
    }


def test_decision_record_validates_all_actions_and_audit_fields() -> None:
    actions = ["approved", "rejected", "modified", "cancelled", "paused"]

    for action in actions:
        payload = decision_kwargs(f"decision-{action}")
        payload["action"] = action
        record = DecisionRecord.model_validate(payload)
        assert record.action == action
        assert record.target_type == "research_question"


def test_decision_record_requires_reason_for_non_approval_actions() -> None:
    payload = decision_kwargs()
    payload["action"] = "rejected"
    payload["reason"] = "   "

    with pytest.raises(ValidationError, match="reason"):
        DecisionRecord.model_validate(payload)


def test_decision_record_rejects_unknown_fields() -> None:
    payload = decision_kwargs()
    payload["invented_field"] = True

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        DecisionRecord.model_validate(payload)


def test_decision_migration_and_idempotent_repository_write(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    assert current_revision(database_path) == LATEST_REVISION

    repository = ProjectRepository(database_path)
    repository.create_project("lychee-m2-decision", "lychee-m2-decision")
    first = repository.record_decision(**decision_kwargs())
    replay = repository.record_decision(**decision_kwargs())

    assert replay == first
    assert len(repository.list_decisions("lychee-m2-decision")) == 1

    conflicting = decision_kwargs()
    conflicting["action"] = "rejected"
    conflicting["reason"] = "需要重新确认"
    with pytest.raises(DecisionConflictError):
        repository.record_decision(**conflicting)
    repository.close()


def test_decisions_are_project_scoped_and_missing_project_rolls_back(tmp_path: Path) -> None:
    database_path = tmp_path / "domain.db"
    upgrade_database(database_path)
    repository = ProjectRepository(database_path)
    repository.create_project("project-a", "thread-a")
    repository.create_project("project-b", "thread-b")

    first = repository.record_decision(
        **{
            **decision_kwargs("decision-a"),
            "project_id": "project-a",
            "thread_id": "thread-a",
        }
    )
    second = repository.record_decision(
        **{
            **decision_kwargs("decision-b"),
            "project_id": "project-b",
            "thread_id": "thread-b",
        }
    )
    assert first.decision_id != second.decision_id
    assert [item.decision_id for item in repository.list_decisions("project-a")] == ["decision-a"]
    assert [item.decision_id for item in repository.list_decisions("project-b")] == ["decision-b"]

    missing = decision_kwargs("decision-missing")
    missing["project_id"] = "missing-project"
    missing["thread_id"] = "missing-thread"
    with pytest.raises(ProjectNotFoundError):
        repository.record_decision(**missing)
    repository.close()
