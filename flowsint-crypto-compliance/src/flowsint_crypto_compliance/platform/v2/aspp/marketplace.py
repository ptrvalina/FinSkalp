"""RFC-0019 Ch.14 — extension marketplace catalog."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.aspp.plugin_manager import get_plugin_manager
from flowsint_crypto_compliance.platform.v2.aspp.types import PluginCategory


def marketplace_catalog() -> dict[str, Any]:
    mgr = get_plugin_manager()
    categories: dict[str, list[dict[str, Any]]] = {
        "connectors": [],
        "rules": [],
        "reports": [],
        "viz": [],
        "ai": [],
        "templates": [],
    }

    _cat_map = {
        PluginCategory.CONNECTOR: "connectors",
        PluginCategory.COLLECTOR: "connectors",
        PluginCategory.RULES_ENGINE: "rules",
        PluginCategory.REPORT_TEMPLATE: "reports",
        PluginCategory.VISUALIZATION: "viz",
        PluginCategory.AI_ASSISTANT: "ai",
        PluginCategory.ANALYTICS: "ai",
        PluginCategory.SANCTIONS: "rules",
        PluginCategory.OCR: "connectors",
        PluginCategory.WORKFLOW_TEMPLATE: "templates",
    }

    for plugin in mgr.list():
        bucket = _cat_map.get(plugin.category, "connectors")
        categories[bucket].append(
            {
                "plugin_id": plugin.plugin_id,
                "category": plugin.category.value,
                "version": plugin.version,
                "name_ru": plugin.name_ru,
                "description_ru": plugin.description_ru,
                "health_status": plugin.health_status,
                "source": plugin.source,
                "installable": True,
                "technical_debt": "TD-ASPP-4" if bucket == "connectors" else None,
            }
        )

    return {
        "rfc": "RFC-0019",
        "chapter": 14,
        "title_ru": "Маркетплейс расширений",
        "categories": list(categories.keys()),
        "items_by_category": categories,
        "total_items": sum(len(v) for v in categories.values()),
        "install_endpoint_stub": "/api/platform/v2/aspp/marketplace/install",
        "principle_ru": "Plugin First — каталог расширений без форков ядра",
    }
