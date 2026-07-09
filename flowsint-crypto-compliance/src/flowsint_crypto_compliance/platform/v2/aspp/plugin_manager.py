"""RFC-0019 Ch.8-9 — plugin manager extending plugin_registry."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.aspp.types import PluginCategory, PluginManifest
from flowsint_crypto_compliance.platform.v2.plugin_registry import PluginDescriptor, PluginKind, get_plugin_registry


_KIND_TO_CATEGORY: dict[PluginKind, PluginCategory] = {
    PluginKind.BLOCKCHAIN: PluginCategory.CONNECTOR,
    PluginKind.OSINT: PluginCategory.COLLECTOR,
    PluginKind.REGISTRY: PluginCategory.CONNECTOR,
    PluginKind.OCR: PluginCategory.OCR,
    PluginKind.SANCTIONS: PluginCategory.SANCTIONS,
    PluginKind.ANALYTICS: PluginCategory.ANALYTICS,
}


class PluginManager:
    """Extended plugin registry with full PluginManifest."""

    def __init__(self) -> None:
        self._plugins: dict[str, PluginManifest] = {}

    def register(self, manifest: PluginManifest) -> None:
        if manifest.plugin_id in self._plugins:
            raise ValueError(f"plugin already registered: {manifest.plugin_id}")
        self._plugins[manifest.plugin_id] = manifest

    def get(self, plugin_id: str) -> PluginManifest | None:
        return self._plugins.get(plugin_id)

    def list(self, category: PluginCategory | None = None) -> list[PluginManifest]:
        rows = list(self._plugins.values())
        if category is None:
            return rows
        return [p for p in rows if p.category == category]

    def manifest(self) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self._plugins.values()]

    def health_summary(self) -> dict[str, int]:
        summary: dict[str, int] = {}
        for p in self._plugins.values():
            summary[p.health_status] = summary.get(p.health_status, 0) + 1
        return summary


_manager: PluginManager | None = None


def get_plugin_manager() -> PluginManager:
    global _manager
    if _manager is None:
        _manager = PluginManager()
        _bootstrap_plugins(_manager)
    return _manager


def reset_plugin_manager() -> None:
    global _manager
    _manager = None


def _descriptor_to_manifest(desc: PluginDescriptor, *, source: str) -> PluginManifest:
    category = _KIND_TO_CATEGORY.get(desc.kind, PluginCategory.ANALYTICS)
    return PluginManifest(
        plugin_id=desc.plugin_id,
        category=category,
        version=desc.version,
        name_ru=desc.plugin_id,
        description_ru=desc.description_ru,
        permissions=["collect", "publish_events"],
        dependencies=[],
        events_published=["OsintMentionFound", "SanctionHitDetected"],
        events_subscribed=[],
        config_schema={"type": "object", "properties": {}},
        health_status="healthy" if desc.factory else "degraded",
        source=source,
        metadata=dict(desc.metadata),
    )


def _bootstrap_plugins(mgr: PluginManager) -> None:
    """Bootstrap from plugin_registry + connector registry + ICF/CRIF categories."""
    for desc in get_plugin_registry().list():
        mgr.register(_descriptor_to_manifest(desc, source="plugin_registry"))

    from flowsint_crypto_compliance.platform.v2.connectors import get_connector_registry
    from flowsint_crypto_compliance.platform.v2.connectors.types import ConnectorCategory

    _connector_cat_map = {
        ConnectorCategory.BLOCKCHAIN: PluginCategory.CONNECTOR,
        ConnectorCategory.BLOCKCHAIN_INTELLIGENCE: PluginCategory.CONNECTOR,
        ConnectorCategory.PUBLIC_EXPLORER: PluginCategory.CONNECTOR,
        ConnectorCategory.REGISTRY: PluginCategory.CONNECTOR,
        ConnectorCategory.OSINT: PluginCategory.COLLECTOR,
        ConnectorCategory.DOCUMENT: PluginCategory.OCR,
    }

    for desc in get_connector_registry().list_descriptors():
        cat = _connector_cat_map.get(desc.category, PluginCategory.CONNECTOR)
        plugin_id = f"connector.{desc.connector_id}"
        if mgr.get(plugin_id):
            continue
        mgr.register(
            PluginManifest(
                plugin_id=plugin_id,
                category=cat,
                version=desc.version,
                name_ru=desc.title_ru or desc.connector_id,
                description_ru=desc.title_ru,
                permissions=["connect", "collect", "health"],
                dependencies=["RFC-0007"],
                events_published=["RegistryRecordImported", "SanctionHitDetected"],
                events_subscribed=[],
                config_schema={"type": "object", "properties": {"api_key": {"type": "string"}}},
                health_status="healthy",
                source="connector_registry",
                metadata={"connector_id": desc.connector_id, "category": desc.category.value},
            )
        )

    _icf_collectors = [
        ("icf.scalpel.onchain", PluginCategory.COLLECTOR, "ICF on-chain collector"),
        ("icf.scalpel.sanctions", PluginCategory.SANCTIONS, "ICF sanctions collector"),
        ("icf.scalpel.darknet", PluginCategory.COLLECTOR, "ICF darknet collector"),
    ]
    for pid, cat, desc_ru in _icf_collectors:
        if mgr.get(pid):
            continue
        mgr.register(
            PluginManifest(
                plugin_id=pid,
                category=cat,
                version="1.0",
                name_ru=pid,
                description_ru=desc_ru,
                permissions=["collect", "schedule"],
                dependencies=["RFC-0014", "RFC-0007"],
                events_published=["OsintMentionFound"],
                events_subscribed=[],
                config_schema={"type": "object"},
                health_status="healthy",
                source="icf",
            )
        )

    _crif_connectors = [
        ("crif.egrul", PluginCategory.CONNECTOR, "ЕГРЮЛ реестр"),
        ("crif.ofac", PluginCategory.SANCTIONS, "OFAC санкции"),
        ("crif.cbr", PluginCategory.CONNECTOR, "ЦБ РФ реестр"),
    ]
    for pid, cat, desc_ru in _crif_connectors:
        if mgr.get(pid):
            continue
        mgr.register(
            PluginManifest(
                plugin_id=pid,
                category=cat,
                version="1.0",
                name_ru=pid,
                description_ru=desc_ru,
                permissions=["check", "screen", "rules_evaluate"],
                dependencies=["RFC-0015", "RFC-0007"],
                events_published=["RegistryRecordImported", "SanctionHitDetected"],
                events_subscribed=[],
                config_schema={"type": "object"},
                health_status="healthy",
                source="crif",
            )
        )

    _platform_plugins = [
        PluginManifest(
            plugin_id="rde.risk_engine",
            category=PluginCategory.ANALYTICS,
            version="2.0.0",
            name_ru="RDE Risk Engine",
            description_ru="Движок оценки риска RFC-0016",
            permissions=["assess", "recommend"],
            dependencies=["RFC-0016"],
            events_published=["RiskUpdated", "RecommendationCreated"],
            events_subscribed=["FusedIntelligenceReady"],
            config_schema={"type": "object"},
            health_status="healthy",
            source="rde",
        ),
        PluginManifest(
            plugin_id="eia.assistant",
            category=PluginCategory.AI_ASSISTANT,
            version="2.0.0",
            name_ru="EIA Assistant",
            description_ru="Объяснимый ИИ ассистент RFC-0018",
            permissions=["assist", "explain"],
            dependencies=["RFC-0018"],
            events_published=["AICompleted", "RecommendationCreated"],
            events_subscribed=["EvidenceCreated", "RiskUpdated"],
            config_schema={"type": "object"},
            health_status="healthy",
            source="eia",
        ),
        PluginManifest(
            plugin_id="eccf.evidence_chain",
            category=PluginCategory.REPORT_TEMPLATE,
            version="2.0.0",
            name_ru="ECCF Evidence Chain",
            description_ru="Цепочка доказательств RFC-0017",
            permissions=["register", "verify", "archive"],
            dependencies=["RFC-0017"],
            events_published=["EvidenceCreated"],
            events_subscribed=["DocumentUploaded"],
            config_schema={"type": "object"},
            health_status="healthy",
            source="eccf",
        ),
    ]
    for manifest in _platform_plugins:
        if not mgr.get(manifest.plugin_id):
            mgr.register(manifest)
