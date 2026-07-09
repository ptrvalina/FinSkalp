"""RFC-0019 API, SDK & Plugin Platform — tests."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from flowsint_crypto_compliance.platform.v2.aspp.constraints import aspp_architectural_constraints
from flowsint_crypto_compliance.platform.v2.aspp.manifest import aspp_manifest
from flowsint_crypto_compliance.platform.v2.aspp.monitoring import reset_aspp_metrics
from flowsint_crypto_compliance.platform.v2.aspp.orchestrator import dispatch_webhook, register_plugin
from flowsint_crypto_compliance.platform.v2.aspp.plugin_manager import get_plugin_manager, reset_plugin_manager
from flowsint_crypto_compliance.platform.v2.aspp.types import PluginCategory, SDKLanguage
from flowsint_crypto_compliance.platform.v2.aspp.webhooks import get_webhook_registry, reset_webhook_registry
from flowsint_crypto_compliance.platform.v2.events import SCHEMA_VERSION


@pytest.fixture(autouse=True)
def reset_aspp_state():
    reset_plugin_manager()
    reset_webhook_registry()
    reset_aspp_metrics()
    yield
    reset_plugin_manager()
    reset_webhook_registry()
    reset_aspp_metrics()


@pytest.fixture
def v2_client():
    from flowsint_crypto_compliance.platform.v2.routes import create_platform_v2_router

    app = FastAPI()
    app.include_router(create_platform_v2_router(), prefix="/api/platform/v2")
    return TestClient(app)


def test_aspp_manifest_principles_and_gateway():
    m = aspp_manifest()
    assert m["rfc"] == "RFC-0019"
    assert m["schema_version"] == "2.0.0"
    assert m["principle"] == "API First, Plugin First"
    assert m["architectural_constraints"]["api_first"] is True
    assert m["architectural_constraints"]["plugin_first"] is True
    gateway = m["gateway"]
    assert gateway["capabilities"]["authentication"]["enabled"] is True
    assert gateway["capabilities"]["rate_limiting"]["enabled"] is True
    assert gateway["capabilities"]["routing"]["enabled"] is True
    assert gateway["capabilities"]["audit"]["enabled"] is True
    assert len(m["plugin_categories"]) == 10


def test_plugin_manifest_registration():
    result = register_plugin(
        {
            "plugin_id": "custom.rules.v1",
            "category": PluginCategory.RULES_ENGINE.value,
            "version": "1.0.0",
            "name_ru": "Пользовательские правила",
            "description_ru": "Тестовый плагин правил",
            "permissions": ["rules.evaluate"],
            "dependencies": ["RFC-0016"],
            "events_published": ["RiskUpdated"],
            "events_subscribed": ["FusedIntelligenceReady"],
        }
    )
    assert result["ok"] is True
    assert result["plugin"]["plugin_id"] == "custom.rules.v1"
    assert result["plugin"]["category"] == "rules_engine"
    mgr = get_plugin_manager()
    stored = mgr.get("custom.rules.v1")
    assert stored is not None
    assert stored.permissions == ["rules.evaluate"]
    assert stored.health_status == "healthy"


def test_event_catalog_versions():
    from flowsint_crypto_compliance.platform.v2.aspp.event_catalog import event_catalog

    catalog = event_catalog()
    assert catalog["event_schema_version"] == SCHEMA_VERSION
    assert catalog["total_events"] >= 30
    for entry in catalog["events"]:
        assert entry["version"] == SCHEMA_VERSION
        assert entry["schema_ref"].startswith("events/")
        assert entry["envelope"] == "PlatformEvent"


def test_webhook_subscribe_and_deliver_stub():
    reg = get_webhook_registry()
    sub = reg.subscribe(
        url="https://example.com/hooks/aspp",
        event_types=["plugin.registered", "investigation.updated"],
    )
    assert sub.subscription_id
    assert sub.active is True

    created = reg.enqueue_delivery(
        event_type="plugin.registered",
        payload={"plugin_id": "test.plugin"},
    )
    assert len(created) == 1
    result = dispatch_webhook(event_type="plugin.registered", payload={"plugin_id": "test.plugin"})
    assert result["ok"] is True
    assert result["delivered"] >= 1


def test_marketplace_categories():
    from flowsint_crypto_compliance.platform.v2.aspp.orchestrator import list_marketplace

    catalog = list_marketplace()
    assert catalog["rfc"] == "RFC-0019"
    assert set(catalog["categories"]) == {"connectors", "rules", "reports", "viz", "ai", "templates"}
    assert catalog["total_items"] > 0
    for cat in catalog["categories"]:
        assert isinstance(catalog["items_by_category"][cat], list)


def test_sdk_manifests_four_languages():
    m = aspp_manifest()
    sdks = m["sdks"]
    assert set(sdks.keys()) == {lang.value for lang in SDKLanguage}
    for lang in SDKLanguage:
        sdk = sdks[lang.value]
        assert sdk["language"] == lang.value
        assert "client" in sdk["modules"]
        assert "events" in sdk["modules"]
        assert "auth" in sdk["modules"]
        assert "plugin_generator" in sdk["modules"]


def test_architectural_constraints():
    constraints = aspp_architectural_constraints()
    assert "direct_knowledge_graph_mutation" in constraints["forbidden_actions"]
    assert "bypass_ingest_pipeline" in constraints["forbidden_actions"]
    assert constraints["mandatory_ingest_path"] is True
    assert constraints["rbac_enforced"] is True


def test_aspp_manifest_api_endpoint(v2_client):
    resp = v2_client.get("/api/platform/v2/aspp/manifest")
    assert resp.status_code == 200
    body = resp.json()
    assert body["rfc"] == "RFC-0019"
    assert body["plugin_count"] > 0
    assert "gateway" in body
    assert "sdks" in body


def test_aspp_rest_catalog_endpoint(v2_client):
    resp = v2_client.get("/api/platform/v2/aspp/rest-catalog")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_routes"] >= 20
    paths = [r["path"] for r in body["routes"]]
    assert "/api/platform/v2/aspp/manifest" in paths
