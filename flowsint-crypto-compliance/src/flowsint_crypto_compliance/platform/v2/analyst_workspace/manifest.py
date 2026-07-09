"""RFC-0010 Analyst Workspace & User Experience manifest."""

from __future__ import annotations

from enum import Enum
from typing import Any


class WorkspaceTab(str, Enum):
    """Ch.3–4 — вкладки единого рабочего пространства аналитика."""

    SUMMARY = "summary"
    ENTITIES = "entities"
    WALLETS = "wallets"
    TIMELINE = "timeline"
    EVIDENCE = "evidence"
    GRAPH = "graph"
    REPORTS = "reports"
    ACTIVITY = "activity"


class NavigationModule(str, Enum):
    """Ch.2 — модули навигации рабочего пространства."""

    DASHBOARD = "dashboard"
    INVESTIGATION_CENTER = "investigation_center"
    GRAPH = "graph"
    TIMELINE = "timeline"
    ENTITY_EXPLORER = "entity_explorer"
    WALLET_EXPLORER = "wallet_explorer"
    EVIDENCE = "evidence"
    OSINT = "osint"
    REGISTRY = "registry"
    AI_ASSISTANT = "ai_assistant"


class NavigationLevel(str, Enum):
    GLOBAL = "global"
    CONTEXTUAL = "contextual"
    LOCAL = "local"


COMMAND_PALETTE_COMMANDS: list[dict[str, str]] = [
    {"id": "open_summary", "label_ru": "Открыть сводку", "shortcut": "Ctrl+1", "level": "contextual"},
    {"id": "open_entities", "label_ru": "Открыть сущности", "shortcut": "Ctrl+2", "level": "contextual"},
    {"id": "open_wallets", "label_ru": "Открыть кошельки", "shortcut": "Ctrl+3", "level": "contextual"},
    {"id": "open_timeline", "label_ru": "Открыть хронологию", "shortcut": "Ctrl+4", "level": "contextual"},
    {"id": "open_evidence", "label_ru": "Открыть доказательства", "shortcut": "Ctrl+5", "level": "contextual"},
    {"id": "open_graph", "label_ru": "Открыть граф", "shortcut": "Ctrl+6", "level": "contextual"},
    {"id": "open_reports", "label_ru": "Открыть отчёты", "shortcut": "Ctrl+7", "level": "contextual"},
    {"id": "open_activity", "label_ru": "Открыть активность", "shortcut": "Ctrl+8", "level": "contextual"},
    {"id": "search_entity", "label_ru": "Найти сущность", "shortcut": "Ctrl+K", "level": "global"},
    {"id": "search_wallet", "label_ru": "Найти кошелёк", "shortcut": "Ctrl+Shift+K", "level": "global"},
    {"id": "run_osint", "label_ru": "Запустить OSINT-сбор", "level": "contextual"},
    {"id": "register_evidence", "label_ru": "Зарегистрировать доказательство", "level": "contextual"},
    {"id": "export_report", "label_ru": "Экспортировать отчёт", "level": "contextual"},
    {"id": "open_compliance", "label_ru": "Открыть комплаенс", "level": "global"},
    {"id": "toggle_theme", "label_ru": "Сменить тему", "level": "global"},
    {"id": "ask_ai", "label_ru": "Спросить AI-ассистента", "level": "contextual"},
]

PERFORMANCE_SLAS: dict[str, str] = {
    "workspace_state_ms": "500",
    "tab_switch_ms": "100",
    "command_palette_open_ms": "50",
    "graph_render_ms": "2000",
    "timeline_page_ms": "300",
    "evidence_list_ms": "400",
}

SYNC_FIELDS: list[str] = [
    "investigation_id",
    "case_ref",
    "active_tab",
    "selected_entity_id",
    "filters",
    "date_range",
    "graph_zoom",
    "panel_layout",
]

PERSONALIZATION: dict[str, Any] = {
    "density": ["comfortable", "compact"],
    "theme": ["light", "dark", "high-contrast"],
    "default_tab": WorkspaceTab.SUMMARY.value,
    "pinned_panels": [],
    "locale": "ru",
}

NOTIFICATION_TYPES: list[dict[str, str]] = [
    {"id": "evidence_registered", "label_ru": "Новое доказательство"},
    {"id": "workflow_changed", "label_ru": "Изменение статуса дела"},
    {"id": "osint_complete", "label_ru": "OSINT-сбор завершён"},
    {"id": "risk_alert", "label_ru": "Предупреждение о риске"},
    {"id": "collaboration_mention", "label_ru": "Упоминание в комментарии"},
]


def analyst_workspace_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0010",
        "schema_version": "10.0.0",
        "title": "Analyst Workspace & User Experience v2.0",
        "status": "complete",
        "principle_ru": "Аналитик работает в едином контексте расследования — все панели, команды и данные синхронизированы",
        "workspace_tabs": [t.value for t in WorkspaceTab],
        "workspace_tabs_ru": {
            WorkspaceTab.SUMMARY.value: "Сводка",
            WorkspaceTab.ENTITIES.value: "Сущности",
            WorkspaceTab.WALLETS.value: "Кошельки",
            WorkspaceTab.TIMELINE.value: "Хронология",
            WorkspaceTab.EVIDENCE.value: "Доказательства",
            WorkspaceTab.GRAPH.value: "Граф",
            WorkspaceTab.REPORTS.value: "Отчёты",
            WorkspaceTab.ACTIVITY.value: "Активность",
        },
        "navigation_modules": [m.value for m in NavigationModule],
        "navigation_levels": [n.value for n in NavigationLevel],
        "navigation_level_ru": {
            NavigationLevel.GLOBAL.value: "Глобальная навигация",
            NavigationLevel.CONTEXTUAL.value: "Контекст расследования",
            NavigationLevel.LOCAL.value: "Локальная панель",
        },
        "command_palette": COMMAND_PALETTE_COMMANDS,
        "performance_slas": PERFORMANCE_SLAS,
        "sync_fields": SYNC_FIELDS,
        "personalization": PERSONALIZATION,
        "notifications": NOTIFICATION_TYPES,
        "multi_window_sync": {
            "enabled": True,
            "transport": "broadcast_channel",
            "channel": "finskalp.workspace.v1",
            "note_ru": "Синхронизация вкладок и контекста между окнами браузера через BroadcastChannel",
        },
        "collaboration": {
            "realtime": "channel",
            "transport": "polling",
            "note_ru": "Комментарии и лента активности; push через polling (WebSocket — prod)",
        },
        "api": {
            "manifest": "/api/platform/v2/analyst-workspace/manifest",
            "state": "GET /api/platform/v2/analyst-workspace/state?case_ref=&investigation_id=",
            "search": "GET /api/platform/v2/analyst-workspace/search?q=&case_ref=",
            "collaboration_comment": "POST /api/platform/v2/analyst-workspace/collaboration/comment",
            "collaboration_activity": "GET /api/platform/v2/analyst-workspace/collaboration/activity?case_ref=",
            "personalization": "GET|PUT /api/platform/v2/analyst-workspace/personalization",
        },
        "depends_on": ["RFC-0005", "RFC-0008"],
    }
