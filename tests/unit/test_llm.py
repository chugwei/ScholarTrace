import json
from collections.abc import Mapping

import httpx
import pytest

from scholartrace.llm import (
    AnthropicCompatibleProvider,
    LLMConfigurationError,
    LLMProviderError,
    LLMSettings,
    propose_research_question,
)

VALID_CANDIDATE: dict[str, object] = {
    "problem": "复杂果园背景中的荔枝病虫害小目标检测",
    "target_population_or_domain": "华南荔枝果园图像",
    "inputs": ["RGB 果园图像"],
    "expected_outputs": ["病虫害类别", "目标边界框"],
    "constraints": ["类别体系尚待领域人员确认"],
    "success_criteria": ["独立测试集指标可复算"],
    "assumptions": ["正式数据已获得合法授权"],
    "unresolved_questions": ["小目标尺寸分层阈值如何确定"],
}


def test_llm_settings_are_disabled_without_key_and_use_safe_defaults() -> None:
    assert LLMSettings.from_env({}) is None

    settings = LLMSettings.from_env({"SCHOLARTRACE_LLM_API_KEY": "  test-secret  "})

    assert settings == LLMSettings(
        base_url="https://api.z.ai/api/anthropic",
        api_key="test-secret",
        model="glm-5.3",
        timeout_seconds=180.0,
        max_tokens=1600,
    )


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"SCHOLARTRACE_LLM_BASE_URL": "http://api.example.test"}, "HTTPS URL"),
        (
            {"SCHOLARTRACE_LLM_BASE_URL": "https://api.example.test?debug=true"},
            "without query or fragment",
        ),
        ({"SCHOLARTRACE_LLM_MODEL": "  "}, "must not be blank"),
        ({"SCHOLARTRACE_LLM_TIMEOUT_SECONDS": "soon"}, "must be a number"),
        ({"SCHOLARTRACE_LLM_TIMEOUT_SECONDS": "0"}, "must be positive"),
    ],
)
def test_llm_settings_reject_invalid_enabled_configuration(
    override: dict[str, str], message: str
) -> None:
    environ = {"SCHOLARTRACE_LLM_API_KEY": "test-secret", **override}

    with pytest.raises(LLMConfigurationError, match=message):
        LLMSettings.from_env(environ)


def test_anthropic_compatible_provider_posts_exact_messages_contract() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url) == "https://api.z.ai/api/anthropic/v1/messages"
        assert request.headers["Authorization"] == "Bearer test-secret"
        assert request.headers["anthropic-version"] == "2023-06-01"
        payload = json.loads(request.content)
        assert payload["model"] == "glm-5.3"
        assert payload["max_tokens"] == 1600
        assert payload["system"] == "Return JSON only."
        assert json.loads(payload["messages"][0]["content"]) == {"problem": "lychee detection"}
        return httpx.Response(
            200,
            json={
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(VALID_CANDIDATE, ensure_ascii=False),
                    }
                ]
            },
            request=request,
        )

    provider = AnthropicCompatibleProvider(
        LLMSettings(
            base_url="https://api.z.ai/api/anthropic",
            api_key="test-secret",
            model="glm-5.3",
        ),
        transport=httpx.MockTransport(handler),
    )

    result = provider.generate_json(
        system_prompt="Return JSON only.",
        input_payload={"problem": "lychee detection"},
    )

    assert result == VALID_CANDIDATE


def test_anthropic_compatible_provider_errors_do_not_leak_api_key() -> None:
    secret = "secret-that-must-not-leak"
    provider = AnthropicCompatibleProvider(
        LLMSettings(
            base_url="https://api.z.ai/api/anthropic",
            api_key=secret,
            model="glm-5.3",
        ),
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                401,
                json={"error": {"message": f"rejected {secret}"}},
                headers={"request-id": "req-test"},
                request=request,
            )
        ),
    )

    with pytest.raises(LLMProviderError, match="HTTP 401") as captured:
        provider.generate_json(system_prompt="Return JSON.", input_payload={"problem": "x"})

    assert secret not in str(captured.value)
    assert secret not in repr(captured.value)


class _FakeProvider:
    name = "fake-provider"
    model = "fake-model"

    def __init__(self) -> None:
        self.input_payload: Mapping[str, object] | None = None

    def generate_json(
        self,
        *,
        system_prompt: str,
        input_payload: Mapping[str, object],
    ) -> Mapping[str, object]:
        assert "Do not invent citations" in system_prompt
        self.input_payload = input_payload
        return VALID_CANDIDATE


def test_propose_research_question_returns_a_validated_candidate() -> None:
    provider = _FakeProvider()

    candidate = propose_research_question(
        provider,
        problem="lychee detection",
        context="Use only reviewed project context.",
    )

    assert candidate.model_dump(mode="json") == VALID_CANDIDATE
    assert provider.input_payload == {
        "problem": "lychee detection",
        "context": "Use only reviewed project context.",
    }
