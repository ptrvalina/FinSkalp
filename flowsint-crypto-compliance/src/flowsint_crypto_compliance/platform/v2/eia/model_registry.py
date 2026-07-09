"""RFC-0018 Ch.14 — LLM provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Abstract LLM provider interface."""

    @abstractmethod
    def complete(self, prompt: str, *, max_tokens: int = 1024) -> str:
        ...


class DeterministicModel(LLMProvider):
    """Stub model — deterministic template-based responses for tests/offline."""

    def complete(self, prompt: str, *, max_tokens: int = 1024) -> str:
        if "explain_risk" in prompt.lower() or "риск" in prompt.lower():
            return (
                "На основании доступных сигналов выявлен повышенный уровень риска. "
                "Рекомендуется проверка источников и подтверждение аналитиком."
            )
        if "ссылк" in prompt.lower() or "link" in prompt.lower():
            return "Обнаружены связи между объектами расследования через граф знаний."
        if "отчёт" in prompt.lower() or "report" in prompt.lower():
            return "Черновик структуры отчёта подготовлен на основе собранных материалов."
        if "противореч" in prompt.lower():
            return "Выявлены потенциальные противоречия между источниками — требуется проверка."
        if "пробел" in prompt.lower() or "gap" in prompt.lower():
            return "Обнаружены пробелы в данных — рекомендуется дополнительный сбор."
        return "Анализ выполнен на основе контекста расследования. Требуется подтверждение аналитиком."


class OpenAICompatibleAdapter(LLMProvider):
    """Stub OpenAI-compatible adapter — requires API key (TD-EIA-1)."""

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini") -> None:
        self.api_key = api_key
        self.model = model

    def complete(self, prompt: str, *, max_tokens: int = 1024) -> str:
        if not self.api_key:
            raise RuntimeError("OpenAI API key not configured (TD-EIA-1)")
        # Stub — real HTTP call deferred to TD-EIA-1
        return DeterministicModel().complete(prompt, max_tokens=max_tokens)


_default_provider: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    global _default_provider
    if _default_provider is None:
        import os

        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            _default_provider = OpenAICompatibleAdapter(api_key=api_key)
        else:
            _default_provider = DeterministicModel()
    return _default_provider


def set_llm_provider(provider: LLMProvider) -> None:
    global _default_provider
    _default_provider = provider


def model_registry_manifest() -> dict[str, Any]:
    return {
        "providers": ["DeterministicModel", "OpenAICompatibleAdapter"],
        "default": "DeterministicModel",
        "env_key": "OPENAI_API_KEY",
        "streaming": False,
        "note": "Real LLM integration deferred to TD-EIA-1",
    }
