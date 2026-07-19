"""Plugin registry — RFC-0002 Chapter 14."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class PluginKind(str, Enum):
    BLOCKCHAIN = "blockchain"
    OSINT = "osint"
    REGISTRY = "registry"
    OCR = "ocr"
    SANCTIONS = "sanctions"
    ANALYTICS = "analytics"


@dataclass
class PluginDescriptor:
    plugin_id: str
    kind: PluginKind
    version: str
    description_ru: str = ""
    factory: Callable[..., Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class PluginRegistry:
    """Register acquisition/analytics plugins without modifying core."""

    def __init__(self) -> None:
        self._plugins: dict[str, PluginDescriptor] = {}

    def register(self, descriptor: PluginDescriptor) -> None:
        if descriptor.plugin_id in self._plugins:
            raise ValueError(f"plugin already registered: {descriptor.plugin_id}")
        self._plugins[descriptor.plugin_id] = descriptor

    def get(self, plugin_id: str) -> PluginDescriptor | None:
        return self._plugins.get(plugin_id)

    def list(self, kind: PluginKind | None = None) -> list[PluginDescriptor]:
        rows = list(self._plugins.values())
        if kind is None:
            return rows
        return [p for p in rows if p.kind == kind]

    def manifest(self) -> list[dict[str, Any]]:
        return [
            {
                "plugin_id": p.plugin_id,
                "kind": p.kind.value,
                "version": p.version,
                "description_ru": p.description_ru,
            }
            for p in self._plugins.values()
        ]


_registry: PluginRegistry | None = None


def get_plugin_registry() -> PluginRegistry:
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
        _bootstrap_defaults(_registry)
    return _registry


def _scalpel_collector_factory(collector_cls: type) -> Callable[..., Any]:
    def factory(**kwargs: Any) -> Any:
        return collector_cls(**kwargs)

    return factory


def _bootstrap_defaults(reg: PluginRegistry) -> None:
    """Register known v1 collectors as plugin descriptors with factories."""
    from flowsint_crypto_compliance.osint_core.scalpel.collectors.abuse_scam_registry import (
        AbuseScamRegistryCollector,
    )
    from flowsint_crypto_compliance.osint_core.scalpel.collectors.clearnet_intel import (
        ClearnetIntelCollector,
    )
    from flowsint_crypto_compliance.osint_core.scalpel.collectors.court_enforcement import (
        CourtEnforcementCollector,
    )
    from flowsint_crypto_compliance.osint_core.scalpel.collectors.darknet_index import DarknetIndexCollector
    from flowsint_crypto_compliance.osint_core.scalpel.collectors.darknet_tor import DarknetTorCollector
    from flowsint_crypto_compliance.osint_core.scalpel.collectors.onchain_explorer import OnchainExplorerCollector
    from flowsint_crypto_compliance.osint_core.scalpel.collectors.reverse_whois_dns import (
        ReverseWhoisDnsCollector,
    )
    from flowsint_crypto_compliance.osint_core.scalpel.collectors.sanctions_watchlist import (
        SanctionsWatchlistCollector,
    )
    from flowsint_crypto_compliance.osint_core.scalpel.collectors.username_probe import (
        UsernameProbeCollector,
    )
    from flowsint_crypto_compliance.osint_core.scalpel.collectors.username_social import UsernameSocialCollector
    from flowsint_crypto_compliance.osint_core.scalpel.collectors.vasp_registry import VaspRegistryCollector

    defaults: list[tuple[str, PluginKind, str, str, Callable[..., Any] | None]] = [
        ("scalpel.onchain", PluginKind.BLOCKCHAIN, "1.0", "On-chain explorer", _scalpel_collector_factory(OnchainExplorerCollector)),
        ("scalpel.sanctions", PluginKind.SANCTIONS, "1.0", "Санкционные списки", _scalpel_collector_factory(SanctionsWatchlistCollector)),
        ("scalpel.darknet", PluginKind.OSINT, "1.0", "Darknet / Ahmia", _scalpel_collector_factory(DarknetIndexCollector)),
        ("scalpel.darknet_tor", PluginKind.OSINT, "1.0", "Darknet Tor", _scalpel_collector_factory(DarknetTorCollector)),
        ("scalpel.username", PluginKind.OSINT, "1.0", "Username / social", _scalpel_collector_factory(UsernameSocialCollector)),
        ("scalpel.username_probe", PluginKind.OSINT, "1.0", "Username probe", _scalpel_collector_factory(UsernameProbeCollector)),
        ("scalpel.abuse", PluginKind.REGISTRY, "1.0", "Abuse registry", _scalpel_collector_factory(AbuseScamRegistryCollector)),
        ("scalpel.clearnet", PluginKind.OSINT, "1.0", "Clearnet intel", _scalpel_collector_factory(ClearnetIntelCollector)),
        ("scalpel.court", PluginKind.OSINT, "1.0", "Court / enforcement", _scalpel_collector_factory(CourtEnforcementCollector)),
        ("scalpel.dns", PluginKind.OSINT, "1.0", "Reverse WHOIS / DNS", _scalpel_collector_factory(ReverseWhoisDnsCollector)),
        ("scalpel.vasp", PluginKind.REGISTRY, "1.0", "VASP registry", _scalpel_collector_factory(VaspRegistryCollector)),
        ("ocr.paddle", PluginKind.OCR, "1.0", "OCR документов", None),
        ("analytics.xgboost", PluginKind.ANALYTICS, "1.0", "ML risk scoring", None),
    ]
    for pid, kind, ver, desc, factory in defaults:
        reg.register(
            PluginDescriptor(
                plugin_id=pid,
                kind=kind,
                version=ver,
                description_ru=desc,
                factory=factory,
                metadata={"scalpel": pid.startswith("scalpel.")},
            )
        )


def create_scalpel_collector(plugin_id: str, **kwargs: Any) -> Any:
    """Instantiate a registered Scalpel collector by plugin_id."""
    desc = get_plugin_registry().get(plugin_id)
    if not desc or not desc.factory:
        raise ValueError(f"collector plugin not available: {plugin_id}")
    if "gateway" not in kwargs:
        from flowsint_crypto_compliance.osint_core.scalpel.network_gateway import NetworkGateway

        kwargs.setdefault("gateway", NetworkGateway())
    return desc.factory(**kwargs)
