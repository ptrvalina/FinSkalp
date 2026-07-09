"""RFC-0019 ASPP v2.0 — core types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PluginCategory(str, Enum):
    """RFC-0019 Ch.8 — ten plugin categories."""

    CONNECTOR = "connector"
    COLLECTOR = "collector"
    ANALYTICS = "analytics"
    RULES_ENGINE = "rules_engine"
    REPORT_TEMPLATE = "report_template"
    VISUALIZATION = "visualization"
    AI_ASSISTANT = "ai_assistant"
    SANCTIONS = "sanctions"
    OCR = "ocr"
    WORKFLOW_TEMPLATE = "workflow_template"


class APIVersion(str, Enum):
    V2_0_0 = "2.0.0"
    V2_1_0_BETA = "2.1.0-beta"


class WebhookEventType(str, Enum):
    PLUGIN_REGISTERED = "plugin.registered"
    PLUGIN_HEALTH_CHANGED = "plugin.health_changed"
    API_RATE_LIMITED = "api.rate_limited"
    INVESTIGATION_UPDATED = "investigation.updated"
    EVIDENCE_CREATED = "evidence.created"
    RISK_UPDATED = "risk.updated"
    MARKETPLACE_ITEM_PUBLISHED = "marketplace.item_published"
    WEBHOOK_DELIVERY_FAILED = "webhook.delivery_failed"


class SDKLanguage(str, Enum):
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    GO = "go"
    JAVA = "java"


@dataclass
class PluginManifest:
    """RFC-0019 Ch.8-9 — full plugin manifest."""

    plugin_id: str
    category: PluginCategory
    version: str
    name_ru: str = ""
    description_ru: str = ""
    permissions: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    events_published: list[str] = field(default_factory=list)
    events_subscribed: list[str] = field(default_factory=list)
    config_schema: dict[str, Any] = field(default_factory=dict)
    health_status: str = "healthy"
    source: str = "aspp"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "category": self.category.value,
            "version": self.version,
            "name_ru": self.name_ru,
            "description_ru": self.description_ru,
            "permissions": list(self.permissions),
            "dependencies": list(self.dependencies),
            "events_published": list(self.events_published),
            "events_subscribed": list(self.events_subscribed),
            "config_schema": dict(self.config_schema),
            "health_status": self.health_status,
            "source": self.source,
            "metadata": dict(self.metadata),
        }


@dataclass
class WebhookSubscription:
    subscription_id: str
    url: str
    event_types: list[str]
    secret: str = ""
    active: bool = True
    retry_count: int = 0
    max_retries: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "subscription_id": self.subscription_id,
            "url": self.url,
            "event_types": list(self.event_types),
            "active": self.active,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "metadata": dict(self.metadata),
        }
