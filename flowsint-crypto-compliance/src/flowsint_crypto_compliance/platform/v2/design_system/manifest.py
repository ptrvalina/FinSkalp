"""RFC-0008 Enterprise Design System — platform manifest."""

from __future__ import annotations

from typing import Any

DESIGN_PRINCIPLES = [
    {"id": "investigation_first", "label_ru": "Investigation First — всё в контексте расследования"},
    {"id": "information_density", "label_ru": "Information Density — много данных без шума"},
    {"id": "progressive_disclosure", "label_ru": "Progressive Disclosure — детали по запросу"},
    {"id": "explainability", "label_ru": "Explainability — любой показатель объясним"},
    {"id": "context_preservation", "label_ru": "Context Preservation — фильтры и сущность сохраняются"},
]

THEMES = ["light", "dark", "high-contrast"]

SPACING_PX = [4, 8, 16, 24, 32, 48]

TYPOGRAPHY = ["h1", "h2", "h3", "h4", "body-lg", "body", "caption", "label"]

SEMANTIC_COLORS = ["success", "warning", "error", "info"]

RISK_COLORS = ["low", "medium", "high", "critical"]

GRAPH_ENTITY_COLORS = [
    "wallet",
    "person",
    "company",
    "exchange",
    "contract",
    "document",
    "evidence",
    "investigation",
]

REQUIRED_COMPONENTS: dict[str, list[str]] = {
    "navigation": ["Sidebar", "TopBar", "Breadcrumbs", "CommandPalette"],
    "forms": ["Input", "Search", "Select", "MultiSelect", "DateRange", "Upload", "TagEditor"],
    "tables": ["Table", "DataTable"],
    "cards": ["Card", "WalletCard", "InvestigationCard", "EvidenceCard"],
    "graph": ["ReactFlow", "Minimap", "Controls", "Background"],
    "timeline": ["ActivityTimeline"],
    "dashboards": ["CompliancePage", "MetricsGrid"],
}

ENTITY_ICONS = [
    "person",
    "company",
    "bank",
    "wallet",
    "document",
    "evidence",
    "report",
    "domain",
    "device",
    "investigation",
]

BREAKPOINTS = {
    "laptop": 1280,
    "desktop": 1920,
    "wide": 2560,
    "ultraWide": 3440,
}


def design_system_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0008",
        "schema_version": "8.0.0",
        "title": "Enterprise Design System v2.0",
        "status": "complete",
        "principles": DESIGN_PRINCIPLES,
        "themes": THEMES,
        "spacing_px": SPACING_PX,
        "typography": TYPOGRAPHY,
        "semantic_colors": SEMANTIC_COLORS,
        "risk_colors": RISK_COLORS,
        "graph_entity_colors": GRAPH_ENTITY_COLORS,
        "entity_icons": ENTITY_ICONS,
        "components": REQUIRED_COMPONENTS,
        "breakpoints": BREAKPOINTS,
        "token_css": "flowsint-app/src/design-system/tokens.css",
        "governance": {
            "requires": [
                "description",
                "api",
                "variants",
                "states",
                "a11y",
                "examples",
                "tests",
            ],
        },
        "philosophy_ru": (
            "Дизайн FinSkalp — часть аналитического процесса: высокая плотность данных, "
            "прогрессивное раскрытие и сохранение контекста расследования."
        ),
    }
