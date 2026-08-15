"""Minimal, server-side LLM integration for validated research candidates."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlsplit

import httpx
from pydantic import ValidationError

from scholartrace.schemas.research import ResearchQuestion


class LLMConfigurationError(ValueError):
    """Raised when an enabled LLM configuration is malformed."""


class LLMProviderError(RuntimeError):
    """Raised when the configured upstream provider cannot return usable JSON."""


class LLMOutputValidationError(ValueError):
    """Raised when an LLM candidate violates a ScholarTrace domain contract."""


@dataclass(frozen=True, slots=True)
class LLMSettings:
    """Environment-backed settings; the API key never crosses the server boundary."""

    base_url: str
    api_key: str
    model: str
    timeout_seconds: float = 180.0
    max_tokens: int = 1600

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> LLMSettings | None:
        source = os.environ if environ is None else environ
        api_key = source.get("SCHOLARTRACE_LLM_API_KEY", "").strip()
        if not api_key:
            return None
        base_url = source.get("SCHOLARTRACE_LLM_BASE_URL", "https://api.z.ai/api/anthropic").strip()
        model = source.get("SCHOLARTRACE_LLM_MODEL", "glm-5.3").strip()
        timeout_text = source.get("SCHOLARTRACE_LLM_TIMEOUT_SECONDS", "180").strip()
        try:
            timeout_seconds = float(timeout_text)
        except ValueError as error:
            raise LLMConfigurationError(
                "SCHOLARTRACE_LLM_TIMEOUT_SECONDS must be a number"
            ) from error
        parsed = urlsplit(base_url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
            raise LLMConfigurationError(
                "SCHOLARTRACE_LLM_BASE_URL must be an HTTPS URL without query or fragment"
            )
        if not model:
            raise LLMConfigurationError("SCHOLARTRACE_LLM_MODEL must not be blank")
        if timeout_seconds <= 0:
            raise LLMConfigurationError("SCHOLARTRACE_LLM_TIMEOUT_SECONDS must be positive")
        return cls(
            base_url=base_url.rstrip("/"),
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
        )


class StructuredLLMProvider(Protocol):
    """Small provider boundary for JSON candidates, not autonomous research actions."""

    @property
    def name(self) -> str: ...

    @property
    def model(self) -> str: ...

    def generate_json(
        self,
        *,
        system_prompt: str,
        input_payload: Mapping[str, object],
    ) -> Mapping[str, object]: ...


class AnthropicCompatibleProvider:
    """Call an Anthropic Messages-compatible endpoint with Bearer authentication."""

    def __init__(
        self,
        settings: LLMSettings,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._transport = transport

    @property
    def name(self) -> str:
        return "anthropic-compatible"

    @property
    def model(self) -> str:
        return self._settings.model

    def generate_json(
        self,
        *,
        system_prompt: str,
        input_payload: Mapping[str, object],
    ) -> Mapping[str, object]:
        timeout = httpx.Timeout(self._settings.timeout_seconds, connect=10.0)
        headers = {
            "Authorization": f"Bearer {self._settings.api_key}",
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        request_payload = {
            "model": self.model,
            "max_tokens": self._settings.max_tokens,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": json.dumps(input_payload, ensure_ascii=False, sort_keys=True),
                }
            ],
        }
        with httpx.Client(
            base_url=self._settings.base_url + "/",
            timeout=timeout,
            transport=self._transport,
        ) as client:
            response: httpx.Response | None = None
            for attempt in range(2):
                try:
                    response = client.post("v1/messages", headers=headers, json=request_payload)
                except httpx.TransportError as error:
                    if attempt == 0:
                        time.sleep(0.25)
                        continue
                    raise LLMProviderError("LLM upstream request failed") from error
                if attempt == 0 and _is_retryable(response):
                    time.sleep(0.25)
                    continue
                break
        if response is None:
            raise LLMProviderError("LLM upstream returned no response")
        if response.is_error:
            request_id = response.headers.get("request-id") or response.headers.get("x-request-id")
            suffix = f" (request {request_id})" if request_id else ""
            raise LLMProviderError(f"LLM upstream returned HTTP {response.status_code}{suffix}")
        return _parse_anthropic_json(response)


def load_llm_provider_from_env(
    environ: Mapping[str, str] | None = None,
) -> StructuredLLMProvider | None:
    settings = LLMSettings.from_env(environ)
    return AnthropicCompatibleProvider(settings) if settings is not None else None


def propose_research_question(
    provider: StructuredLLMProvider,
    *,
    problem: str,
    context: str | None = None,
) -> ResearchQuestion:
    """Generate and strictly validate a non-persistent research-question candidate."""

    system_prompt = """You create a structured research-question candidate for ScholarTrace.
Return exactly one JSON object with these keys: problem, target_population_or_domain, inputs,
expected_outputs, constraints, success_criteria, assumptions, unresolved_questions.
All list fields must be JSON arrays of strings. Do not invent citations, DOI, authors, dates,
datasets, experimental metrics, approvals, or verified conclusions. Put uncertainty in
assumptions or unresolved_questions. Output JSON only, with no prose or Markdown fences."""
    payload: dict[str, object] = {"problem": problem}
    if context:
        payload["context"] = context
    try:
        candidate = provider.generate_json(system_prompt=system_prompt, input_payload=payload)
        return ResearchQuestion.model_validate(candidate)
    except LLMProviderError:
        raise
    except (TypeError, ValidationError, ValueError) as error:
        raise LLMOutputValidationError(
            "LLM output did not satisfy the ResearchQuestion contract"
        ) from error


def _is_retryable(response: httpx.Response) -> bool:
    if response.status_code >= 500:
        return True
    if response.status_code != 429:
        return False
    try:
        code = str(response.json().get("error", {}).get("code", ""))
    except (AttributeError, ValueError):
        return False
    return code in {"1302", "1305"}


def _parse_anthropic_json(response: httpx.Response) -> Mapping[str, object]:
    try:
        body = response.json()
        blocks = body["content"]
        text = "".join(
            block["text"]
            for block in blocks
            if isinstance(block, dict) and block.get("type") == "text"
        ).strip()
        parsed = json.loads(_strip_code_fence(text))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise LLMProviderError("LLM upstream returned an invalid JSON message") from error
    if not isinstance(parsed, dict):
        raise LLMProviderError("LLM upstream JSON must be an object")
    return parsed


def _strip_code_fence(text: str) -> str:
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if len(lines) >= 3 and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1])
    return text
