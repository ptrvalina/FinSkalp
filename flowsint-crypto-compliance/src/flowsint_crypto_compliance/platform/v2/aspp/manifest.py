"""RFC-0019 ASPP v2.0 manifest."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.aspp.constraints import aspp_architectural_constraints
from flowsint_crypto_compliance.platform.v2.aspp.developer_portal import developer_portal_manifest
from flowsint_crypto_compliance.platform.v2.aspp.event_catalog import event_catalog
from flowsint_crypto_compliance.platform.v2.aspp.gateway_manifest import gateway_capabilities_manifest
from flowsint_crypto_compliance.platform.v2.aspp.graphql_schema import graphql_manifest
from flowsint_crypto_compliance.platform.v2.aspp.grpc_manifest import grpc_manifest
from flowsint_crypto_compliance.platform.v2.aspp.plugin_manager import get_plugin_manager
from flowsint_crypto_compliance.platform.v2.aspp.rest_catalog import rest_catalog
from flowsint_crypto_compliance.platform.v2.aspp.sdk_go import go_sdk_manifest
from flowsint_crypto_compliance.platform.v2.aspp.sdk_java import java_sdk_manifest
from flowsint_crypto_compliance.platform.v2.aspp.sdk_python import python_sdk_manifest
from flowsint_crypto_compliance.platform.v2.aspp.sdk_typescript import typescript_sdk_manifest
from flowsint_crypto_compliance.platform.v2.aspp.security_manifest import security_manifest
from flowsint_crypto_compliance.platform.v2.aspp.types import PluginCategory, SDKLanguage
from flowsint_crypto_compliance.platform.v2.aspp.versioning import PLATFORM_API_VERSION, platform_version_manifest
from flowsint_crypto_compliance.platform.v2.aspp.webhooks import supported_webhook_event_types


def aspp_manifest() -> dict[str, Any]:
    mgr = get_plugin_manager()
    return {
        "rfc": "RFC-0019",
        "schema_version": PLATFORM_API_VERSION,
        "title": "API, SDK & Plugin Platform v2.0",
        "title_ru": "API, SDK и платформа плагинов v2.0",
        "principle": "API First, Plugin First",
        "principle_ru": "API First, Plugin First — расширения через манифест, без форков ядра",
        "chapters": list(range(1, 21)),
        "versioning": platform_version_manifest(),
        "gateway": gateway_capabilities_manifest(),
        "rest_catalog_summary": {
            "total_routes": rest_catalog()["total_routes"],
            "endpoint": "/api/platform/v2/aspp/rest-catalog",
        },
        "graphql": graphql_manifest(),
        "grpc": grpc_manifest(),
        "event_catalog_summary": {
            "total_events": event_catalog()["total_events"],
            "endpoint": "/api/platform/v2/aspp/events",
        },
        "plugin_categories": [c.value for c in PluginCategory],
        "plugin_count": len(mgr.list()),
        "sdks": {
            SDKLanguage.PYTHON.value: python_sdk_manifest(),
            SDKLanguage.TYPESCRIPT.value: typescript_sdk_manifest(),
            SDKLanguage.GO.value: go_sdk_manifest(),
            SDKLanguage.JAVA.value: java_sdk_manifest(),
        },
        "security": security_manifest(),
        "webhook_event_types": supported_webhook_event_types(),
        "architectural_constraints": aspp_architectural_constraints(),
        "developer_portal": developer_portal_manifest(),
        "api": {
            "manifest": "/api/platform/v2/aspp/manifest",
            "rest_catalog": "/api/platform/v2/aspp/rest-catalog",
            "events": "/api/platform/v2/aspp/events",
            "marketplace": "/api/platform/v2/aspp/marketplace",
            "developer_portal": "/api/platform/v2/aspp/developer-portal",
            "webhooks_subscribe": "/api/platform/v2/aspp/webhooks/subscribe",
            "webhooks_list": "/api/platform/v2/aspp/webhooks",
            "monitoring": "/api/platform/v2/aspp/monitoring",
            "plugins_register": "/api/platform/v2/aspp/plugins/register",
        },
    }
