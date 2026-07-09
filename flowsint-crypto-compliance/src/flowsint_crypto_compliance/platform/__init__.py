"""FinSkalp platform v2 — canonical investigation architecture (RFC-0002)."""

from flowsint_crypto_compliance.platform.v2.canonical import (
    Entity,
    EntityAttribute,
    EntityRelation,
    EntityType,
    Evidence,
    TrustLevel,
)
from flowsint_crypto_compliance.platform.v2.events import EventType, PlatformEvent
from flowsint_crypto_compliance.platform.v2.event_bus import PlatformEventBus, get_platform_event_bus
from flowsint_crypto_compliance.platform.v2.fusion_pipeline import FusionPipeline, FusionStage
from flowsint_crypto_compliance.platform.v2.plugin_registry import PluginKind, PluginRegistry, get_plugin_registry

__all__ = [
    "Entity",
    "EntityAttribute",
    "EntityRelation",
    "EntityType",
    "Evidence",
    "TrustLevel",
    "EventType",
    "PlatformEvent",
    "PlatformEventBus",
    "get_platform_event_bus",
    "FusionPipeline",
    "FusionStage",
    "PluginKind",
    "PluginRegistry",
    "get_plugin_registry",
]
