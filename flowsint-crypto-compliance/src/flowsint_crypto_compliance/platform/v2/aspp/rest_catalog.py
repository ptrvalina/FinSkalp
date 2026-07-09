"""RFC-0019 Ch.4 — REST surface catalog."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.aspp.versioning import PLATFORM_API_VERSION


def _route(
    method: str,
    path: str,
    *,
    summary_ru: str,
    tags: list[str],
    auth: str = "jwt",
) -> dict[str, Any]:
    return {
        "method": method,
        "path": path,
        "summary_ru": summary_ru,
        "tags": tags,
        "auth": auth,
        "openapi": {
            "operationId": f"{method.lower()}_{path.strip('/').replace('/', '_').replace('-', '_')}",
        },
    }


def rest_catalog() -> dict[str, Any]:
    routes: list[dict[str, Any]] = [
        _route("GET", "/api/platform/v2/manifest", summary_ru="Архитектурный манифест v2", tags=["core"]),
        _route("GET", "/api/platform/v2/aspp/manifest", summary_ru="Манифест ASPP v2.0", tags=["aspp"]),
        _route("GET", "/api/platform/v2/aspp/rest-catalog", summary_ru="Каталог REST API", tags=["aspp"]),
        _route("GET", "/api/platform/v2/aspp/events", summary_ru="Каталог событий", tags=["aspp"]),
        _route("GET", "/api/platform/v2/aspp/marketplace", summary_ru="Каталог расширений", tags=["aspp"]),
        _route("GET", "/api/platform/v2/aspp/developer-portal", summary_ru="Портал разработчика", tags=["aspp"]),
        _route("POST", "/api/platform/v2/aspp/webhooks/subscribe", summary_ru="Подписка на webhook", tags=["aspp"]),
        _route("GET", "/api/platform/v2/aspp/webhooks", summary_ru="Список webhook-подписок", tags=["aspp"]),
        _route("GET", "/api/platform/v2/aspp/monitoring", summary_ru="Метрики API и плагинов", tags=["aspp"]),
        _route("POST", "/api/platform/v2/aspp/plugins/register", summary_ru="Регистрация плагина", tags=["aspp"]),
        _route("GET", "/api/platform/v2/plugins", summary_ru="Каталог плагинов v1", tags=["plugins"]),
        _route("GET", "/api/platform/v2/connectors/manifest", summary_ru="Коннекторы RFC-0007", tags=["connectors"]),
        _route("POST", "/api/platform/v2/connectors/{connector_id}/collect", summary_ru="Сбор через коннектор", tags=["connectors"]),
        _route("GET", "/api/platform/v2/icf/manifest", summary_ru="ICF манифест RFC-0014", tags=["icf"]),
        _route("POST", "/api/platform/v2/icf/collect", summary_ru="ICF сбор данных", tags=["icf"]),
        _route("GET", "/api/platform/v2/crif/manifest", summary_ru="CRIF манифест RFC-0015", tags=["crif"]),
        _route("POST", "/api/platform/v2/crif/check", summary_ru="CRIF проверка реестра", tags=["crif"]),
        _route("GET", "/api/platform/v2/rde/manifest", summary_ru="RDE манифест RFC-0016", tags=["rde"]),
        _route("POST", "/api/platform/v2/rde/assess", summary_ru="RDE оценка риска", tags=["rde"]),
        _route("GET", "/api/platform/v2/eccf/manifest", summary_ru="ECCF манифест RFC-0017", tags=["eccf"]),
        _route("POST", "/api/platform/v2/eccf/register", summary_ru="Регистрация доказательства", tags=["eccf"]),
        _route("GET", "/api/platform/v2/eia/manifest", summary_ru="EIA манифест RFC-0018", tags=["eia"]),
        _route("POST", "/api/platform/v2/eia/assist", summary_ru="EIA ассистент", tags=["eia"]),
        _route("GET", "/api/platform/v2/intelligence/manifest", summary_ru="Intelligence Platform", tags=["intelligence"]),
        _route("GET", "/api/platform/v2/investigation/manifest", summary_ru="Investigation Platform", tags=["investigation"]),
        _route("GET", "/api/platform/v2/rbac/manifest", summary_ru="RBAC harmonization", tags=["rbac"]),
        _route("GET", "/api/platform/v2/workflow/manifest", summary_ru="Workflow RFC-0011", tags=["workflow"]),
        _route("GET", "/api/platform/v2/analyst-workspace/manifest", summary_ru="Analyst Workspace", tags=["workspace"]),
        _route("GET", "/api/platform/v2/blockchain-intelligence/manifest", summary_ru="Blockchain Intelligence", tags=["blockchain"]),
        _route("POST", "/api/platform/v2/ingest", summary_ru="Обязательный ingest", tags=["ingest"]),
        _route("GET", "/api/platform/v2/knowledge-model/manifest", summary_ru="Knowledge Graph v2", tags=["knowledge"]),
    ]
    by_tag: dict[str, list[dict[str, Any]]] = {}
    for r in routes:
        for tag in r["tags"]:
            by_tag.setdefault(tag, []).append(r)
    return {
        "rfc": "RFC-0019",
        "chapter": 4,
        "schema_version": PLATFORM_API_VERSION,
        "openapi_version": "3.1.0",
        "base_path": "/api/platform/v2",
        "total_routes": len(routes),
        "routes": routes,
        "routes_by_tag": by_tag,
        "principle_ru": "API First — полный каталог REST до реализации UI",
    }
