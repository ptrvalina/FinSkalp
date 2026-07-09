"""RFC-0011 Ch.1–2, 17–19 — workflow manifest."""

from __future__ import annotations

from typing import Any

OICD_PHASES = [
    {"id": "observe", "label_ru": "Observe — наблюдение"},
    {"id": "investigate", "label_ru": "Investigate — расследование"},
    {"id": "correlate", "label_ru": "Correlate — корреляция"},
    {"id": "decide", "label_ru": "Decide — решение"},
]

INVESTIGATION_LIFECYCLE = [
    {"id": "case_creation", "label_ru": "Создание дела", "mandatory": True},
    {"id": "object_definition", "label_ru": "Определение объекта", "mandatory": True},
    {"id": "auto_collection", "label_ru": "Автоматический сбор", "mandatory": True},
    {"id": "normalization", "label_ru": "Нормализация", "mandatory": True},
    {"id": "fusion", "label_ru": "Fusion", "mandatory": True},
    {"id": "knowledge_graph", "label_ru": "Knowledge Graph", "mandatory": True},
    {"id": "link_search", "label_ru": "Поиск связей", "mandatory": True},
    {"id": "hypothesis_building", "label_ru": "Построение гипотез", "mandatory": True},
    {"id": "hypothesis_validation", "label_ru": "Проверка гипотез", "mandatory": True},
    {"id": "risk_assessment", "label_ru": "Оценка риска", "mandatory": True},
    {"id": "evidence_formation", "label_ru": "Формирование доказательств", "mandatory": True},
    {"id": "report", "label_ru": "Отчёт", "mandatory": True},
    {"id": "archiving", "label_ru": "Архивирование", "mandatory": True},
]

SEED_OBJECT_TYPES = [
    {"id": "wallet", "label_ru": "Криптовалютный адрес"},
    {"id": "organization", "label_ru": "Организация"},
    {"id": "person", "label_ru": "Физическое лицо"},
    {"id": "document", "label_ru": "Документ"},
    {"id": "transaction", "label_ru": "Транзакция"},
    {"id": "group", "label_ru": "Группа объектов"},
]

AUTO_COLLECTORS = [
    "blockchain_collector",
    "registry_collector",
    "osint_collector",
    "ocr",
    "fusion_engine",
    "entity_resolution",
]

UI_EVENTS = [
    "WalletOpened",
    "GraphLoaded",
    "TimelineUpdated",
    "EvidenceLinked",
    "RiskCalculated",
    "RecommendationCreated",
    "ReportUpdated",
]

BUSINESS_RULES_RU = [
    "Пользователь никогда не вводит одни и те же данные дважды",
    "Все проверки выполняются автоматически после появления новой информации",
    "Каждая сущность имеет единственную каноническую карточку",
    "Любое изменение фиксируется в журнале аудита",
    "Все аналитические выводы сопровождаются объяснением",
    "Все автоматические гипотезы требуют подтверждения аналитиком",
    "Ни одна рекомендация не становится решением без участия человека",
]

UX_KPIS = {
    "case_creation_seconds": 30,
    "entity_card_open_ms": 300,
    "tab_switch_ms": 100,
    "graph_build_progress": True,
    "auto_save_state": True,
}

BACKGROUND_TASKS_RU = [
    "обновление графа",
    "поиск новых связей",
    "повторный OSINT",
    "обновление блокчейна",
    "обновление реестров",
    "пересчёт риска",
    "проверка новых документов",
    "обнаружение новых совпадений",
]


def workflow_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0011",
        "schema_version": "11.0.0",
        "title": "Workflow & User Interaction Logic v2.0",
        "status": "complete",
        "philosophy": OICD_PHASES,
        "investigation_lifecycle": INVESTIGATION_LIFECYCLE,
        "seed_object_types": SEED_OBJECT_TYPES,
        "auto_collectors": AUTO_COLLECTORS,
        "ui_events": UI_EVENTS,
        "business_rules_ru": BUSINESS_RULES_RU,
        "ux_kpis": UX_KPIS,
        "background_tasks_ru": BACKGROUND_TASKS_RU,
        "event_driven": True,
        "principle_ru": "Интерфейс ведёт расследование: Observe → Investigate → Correlate → Decide",
        "rule_ru": "Ни один этап жизненного цикла не может быть пропущен",
    }
