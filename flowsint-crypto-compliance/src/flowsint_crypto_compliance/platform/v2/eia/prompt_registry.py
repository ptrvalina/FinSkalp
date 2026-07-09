"""RFC-0018 Ch.13 — versioned prompt template store (in-memory)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class PromptTemplate:
    task_type: str
    version: str
    template: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    author: str = "eia.system"
    changelog: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_type": self.task_type,
            "version": self.version,
            "template": self.template,
            "created_at": self.created_at,
            "author": self.author,
            "changelog": self.changelog,
        }


_DEFAULT_TEMPLATES: dict[str, list[PromptTemplate]] = {
    "summary": [
        PromptTemplate(
            task_type="summary",
            version="1.0.0",
            template=(
                "Составь краткое резюме расследования {case_ref}.\n"
                "Объекты: {entity_keys}\n"
                "Контекст: {context_summary}\n"
                "Только факты из контекста. Без автоматических выводов."
            ),
            changelog="Initial version",
        ),
    ],
    "explain_risk": [
        PromptTemplate(
            task_type="explain_risk",
            version="1.0.0",
            template=(
                "Объясни уровень риска для {entity_key} в деле {case_ref}.\n"
                "Сигналы: {risk_signals}\n"
                "Укажи источники и ограничения. Не принимай решений."
            ),
            changelog="Initial version",
        ),
        PromptTemplate(
            task_type="explain_risk",
            version="1.1.0",
            template=(
                "Объясни уровень риска для {entity_key} в деле {case_ref}.\n"
                "Сигналы: {risk_signals}\n"
                "Факторы: {top_factors}\n"
                "Цитируй evidence_id. Не принимай решений — только объяснение."
            ),
            changelog="Added top_factors and evidence citations",
        ),
    ],
    "describe_links": [
        PromptTemplate(
            task_type="describe_links",
            version="1.0.0",
            template=(
                "Опиши связи объекта {entity_key} в графе знаний.\n"
                "Соседи: {neighbors}\n"
                "Укажи confidence и evidence_id для каждой связи."
            ),
            changelog="Initial version",
        ),
    ],
    "questions": [
        PromptTemplate(
            task_type="questions",
            version="1.0.0",
            template=(
                "Сформулируй открытые вопросы по делу {case_ref}.\n"
                "Контекст: {context_summary}\n"
                "Гипотезы: {hypotheses}"
            ),
            changelog="Initial version",
        ),
    ],
    "report_outline": [
        PromptTemplate(
            task_type="report_outline",
            version="1.0.0",
            template=(
                "Подготовь структуру отчёта по делу {case_ref}.\n"
                "Материалы: {evidence_count} доказательств.\n"
                "Разделы: введение, объекты, хронология, риски, выводы, приложения."
            ),
            changelog="Initial version",
        ),
    ],
    "explain_changes": [
        PromptTemplate(
            task_type="explain_changes",
            version="1.0.0",
            template=(
                "Объясни изменения в деле {case_ref} за период.\n"
                "События: {timeline_events}\n"
                "Без мутации данных."
            ),
            changelog="Initial version",
        ),
    ],
    "contradictions": [
        PromptTemplate(
            task_type="contradictions",
            version="1.0.0",
            template=(
                "Найди противоречия между источниками в деле {case_ref}.\n"
                "Источники: {sources}\n"
                "Только анализ — без автоматических решений."
            ),
            changelog="Initial version",
        ),
    ],
    "data_gaps": [
        PromptTemplate(
            task_type="data_gaps",
            version="1.0.0",
            template=(
                "Определи пробелы в данных по делу {case_ref}.\n"
                "Доступные группы: {acquired_groups}\n"
                "Отсутствующие: {missing_groups}"
            ),
            changelog="Initial version",
        ),
    ],
}

_store: dict[str, list[PromptTemplate]] = {}


def _ensure_store() -> dict[str, list[PromptTemplate]]:
    global _store
    if not _store:
        _store = {k: list(v) for k, v in _DEFAULT_TEMPLATES.items()}
    return _store


def get_prompt_template(task_type: str, *, version: str | None = None) -> PromptTemplate | None:
    store = _ensure_store()
    versions = store.get(task_type, [])
    if not versions:
        return None
    if version:
        for t in versions:
            if t.version == version:
                return t
        return None
    return versions[-1]


def list_prompt_versions(task_type: str) -> list[dict[str, Any]]:
    store = _ensure_store()
    return [t.to_dict() for t in store.get(task_type, [])]


def list_all_prompts() -> dict[str, list[dict[str, Any]]]:
    store = _ensure_store()
    return {task_type: [t.to_dict() for t in versions] for task_type, versions in store.items()}


def register_prompt_template(template: PromptTemplate) -> PromptTemplate:
    store = _ensure_store()
    store.setdefault(template.task_type, []).append(template)
    return template


def reset_prompt_registry() -> None:
    global _store
    _store = {}
