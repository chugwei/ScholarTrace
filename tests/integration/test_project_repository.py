from pathlib import Path

import pytest
from sqlalchemy import inspect

from scholartrace.persistence.database import create_sqlite_engine
from scholartrace.persistence.migrations import (
    INITIAL_REVISION,
    LATEST_REVISION,
    current_revision,
    downgrade_database,
    upgrade_database,
)
from scholartrace.persistence.repository import (
    ProjectIdentityConflictError,
    ProjectNotFoundError,
    ProjectRepository,
    ResearchQuestionFrozenError,
    ResearchQuestionNotFoundError,
    ResearchQuestionVersionConflictError,
)
from scholartrace.schemas import ResearchQuestion


def question(problem: str = "复杂果园背景中的荔枝病虫害小目标检测") -> ResearchQuestion:
    return ResearchQuestion(
        problem=problem,
        target_population_or_domain="华南荔枝果园图像",
        inputs=["RGB 果园图像", "采集条件元数据"],
        expected_outputs=["病虫害类别", "目标边界框"],
        constraints=["类别体系待领域人员确认"],
        success_criteria=["独立测试集指标可复算"],
        assumptions=["正式数据已获得合法授权"],
        unresolved_questions=["小目标尺寸分层阈值如何确定"],
    )


def migrated_repository(database_path: Path) -> ProjectRepository:
    upgrade_database(database_path)
    return ProjectRepository(database_path)


def test_initial_migration_can_upgrade_and_downgrade(tmp_path: Path) -> None:
    database_path = tmp_path / "scholartrace.db"

    upgrade_database(database_path)
    upgrade_database(database_path)

    engine = create_sqlite_engine(database_path)
    assert current_revision(database_path) == LATEST_REVISION
    assert {"projects", "research_questions", "decision_records"} <= set(
        inspect(engine).get_table_names()
    )
    question_columns = {
        column["name"] for column in inspect(engine).get_columns("research_questions")
    }
    assert {"status", "frozen_at", "frozen_by", "parent_research_question_id"} <= question_columns
    engine.dispose()

    downgrade_database(database_path, "0002")

    engine = create_sqlite_engine(database_path)
    assert current_revision(database_path) == "0002"
    question_columns = {
        column["name"] for column in inspect(engine).get_columns("research_questions")
    }
    assert (
        not {"status", "frozen_at", "frozen_by", "parent_research_question_id"} & question_columns
    )
    assert "decision_records" in inspect(engine).get_table_names()
    assert {"projects", "research_questions"} <= set(inspect(engine).get_table_names())
    engine.dispose()

    downgrade_database(database_path, INITIAL_REVISION)

    engine = create_sqlite_engine(database_path)
    assert current_revision(database_path) == INITIAL_REVISION
    assert "decision_records" not in inspect(engine).get_table_names()
    engine.dispose()

    downgrade_database(database_path)

    engine = create_sqlite_engine(database_path)
    assert current_revision(database_path) is None
    assert "projects" not in inspect(engine).get_table_names()
    assert "research_questions" not in inspect(engine).get_table_names()
    engine.dispose()

    upgrade_database(database_path)
    assert current_revision(database_path) == LATEST_REVISION


def test_create_project_is_idempotent_and_persists_after_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "scholartrace.db"
    repository = migrated_repository(database_path)

    first = repository.create_project(
        project_id="lychee-pest-001",
        thread_id="lychee-pest-001",
        current_goal="定义可检验的研究问题",
    )
    second = repository.create_project(
        project_id="lychee-pest-001",
        thread_id="lychee-pest-001",
        current_goal="定义可检验的研究问题",
    )
    repository.close()

    reopened = ProjectRepository(database_path)
    assert first == second
    assert reopened.get_project("lychee-pest-001") == first
    assert [project.project_id for project in reopened.list_projects()] == ["lychee-pest-001"]
    reopened.close()


@pytest.mark.parametrize(
    ("project_id", "thread_id"),
    [
        ("", "thread-1"),
        ("project/escape", "thread-1"),
        ("project-1", "thread\\escape"),
        (" project-1", "thread-1"),
        ("p" * 129, "thread-1"),
    ],
)
def test_repository_rejects_unsafe_identifiers(
    tmp_path: Path,
    project_id: str,
    thread_id: str,
) -> None:
    repository = migrated_repository(tmp_path / "scholartrace.db")

    with pytest.raises(ValueError, match="identifier"):
        repository.create_project(project_id, thread_id)

    assert repository.list_projects() == []
    repository.close()


@pytest.mark.parametrize(
    ("second_project_id", "second_thread_id"),
    [
        ("lychee-pest-001", "different-thread"),
        ("different-project", "lychee-pest-001"),
    ],
)
def test_project_identity_conflicts_roll_back_cleanly(
    tmp_path: Path,
    second_project_id: str,
    second_thread_id: str,
) -> None:
    repository = migrated_repository(tmp_path / "scholartrace.db")
    repository.create_project("lychee-pest-001", "lychee-pest-001")

    with pytest.raises(ProjectIdentityConflictError):
        repository.create_project(second_project_id, second_thread_id)

    recovered = repository.create_project("orchard-count-001", "orchard-count-001")
    assert recovered.project_id == "orchard-count-001"
    assert len(repository.list_projects()) == 2
    repository.close()


def test_research_question_save_is_idempotent_and_versioned(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "scholartrace.db")
    repository.create_project("lychee-pest-001", "lychee-pest-001")

    first = repository.save_research_question("lychee-pest-001", question())
    replay = repository.save_research_question("lychee-pest-001", question())
    revised = repository.save_research_question(
        "lychee-pest-001",
        question("遮挡与尺度变化下的荔枝病虫害小目标检测"),
    )

    assert replay == first
    assert first.version == 1
    assert revised.version == 2
    assert len(repository.list_research_questions("lychee-pest-001")) == 2
    repository.close()

    reopened = ProjectRepository(tmp_path / "scholartrace.db")
    assert reopened.get_research_question("lychee-pest-001", first.research_question_id) == first
    reopened.close()


def test_frozen_question_requires_explicit_descendant_version(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "scholartrace.db")
    repository.create_project("lychee-pest-001", "lychee-pest-001")

    first = repository.save_research_question("lychee-pest-001", question())
    frozen = repository.freeze_research_question(
        "lychee-pest-001",
        first.research_question_id,
        "researcher-001",
    )
    assert frozen.status == "frozen"
    assert frozen.frozen_by == "researcher-001"
    assert frozen.frozen_at is not None
    assert (
        repository.freeze_research_question(
            "lychee-pest-001",
            first.research_question_id,
            "researcher-001",
        )
        == frozen
    )

    revised_question = question("遮挡与尺度变化下的荔枝病虫害小目标检测")
    with pytest.raises(ResearchQuestionFrozenError, match="frozen"):
        repository.save_research_question("lychee-pest-001", revised_question)

    second = repository.create_research_question_version(
        "lychee-pest-001",
        first.research_question_id,
        revised_question,
        active_stage="awaiting_approval",
    )
    assert second.version == 2
    assert second.status == "draft"
    assert second.parent_research_question_id == first.research_question_id
    with pytest.raises(ResearchQuestionVersionConflictError, match="current"):
        repository.create_research_question_version(
            "lychee-pest-001",
            first.research_question_id,
            question("第三个未经当前版本批准的研究问题"),
        )
    repository.close()


def test_research_questions_are_project_scoped(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "scholartrace.db")
    repository.create_project("project-a", "thread-a")
    repository.create_project("project-b", "thread-b")
    project_a_question = repository.save_research_question("project-a", question())
    project_b_question = repository.save_research_question("project-b", question())

    assert project_a_question.research_question_id != project_b_question.research_question_id
    assert (
        repository.get_research_question(
            "project-a", project_a_question.research_question_id
        ).question
        == question()
    )
    with pytest.raises(ResearchQuestionNotFoundError):
        repository.get_research_question("project-b", project_a_question.research_question_id)
    repository.close()


def test_missing_project_does_not_leave_partial_question(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "scholartrace.db")

    with pytest.raises(ProjectNotFoundError):
        repository.save_research_question("missing-project", question())

    repository.create_project("valid-project", "valid-thread")
    assert repository.list_research_questions("valid-project") == []
    repository.close()
