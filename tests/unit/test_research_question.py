import pytest
from pydantic import ValidationError

from scholartrace.schemas.research import ResearchQuestion


def valid_research_question() -> dict[str, object]:
    return {
        "problem": "复杂果园背景中的荔枝病虫害小目标检测",
        "target_population_or_domain": "华南荔枝果园图像",
        "inputs": ["RGB 果园图像", "采集条件元数据"],
        "expected_outputs": ["病虫害类别", "目标边界框"],
        "constraints": ["类别体系尚待领域人员确认"],
        "success_criteria": ["独立测试集指标可复算"],
        "assumptions": ["正式数据已获得合法授权"],
        "unresolved_questions": ["小目标尺寸分层阈值如何确定"],
    }


def test_research_question_preserves_the_complete_contract() -> None:
    question = ResearchQuestion.model_validate(valid_research_question())

    assert question.problem == "复杂果园背景中的荔枝病虫害小目标检测"
    assert question.inputs == ["RGB 果园图像", "采集条件元数据"]
    assert question.model_dump(mode="json") == valid_research_question()


@pytest.mark.parametrize("field", ["problem", "target_population_or_domain"])
def test_research_question_rejects_blank_required_text(field: str) -> None:
    payload = valid_research_question()
    payload[field] = "   "

    with pytest.raises(ValidationError):
        ResearchQuestion.model_validate(payload)


@pytest.mark.parametrize("field", ["inputs", "expected_outputs", "success_criteria"])
def test_research_question_requires_non_empty_core_lists(field: str) -> None:
    payload = valid_research_question()
    payload[field] = []

    with pytest.raises(ValidationError):
        ResearchQuestion.model_validate(payload)


def test_research_question_rejects_blank_list_items() -> None:
    payload = valid_research_question()
    payload["inputs"] = ["RGB 图像", "  "]

    with pytest.raises(ValidationError):
        ResearchQuestion.model_validate(payload)


def test_research_question_rejects_unknown_fields() -> None:
    payload = valid_research_question()
    payload["invented_metric"] = 0.99

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ResearchQuestion.model_validate(payload)
