"""RFC-0019 Ch.13 — webhook registry + subscribe/deliver stubs with retry."""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.platform.v2.aspp.types import WebhookEventType, WebhookSubscription


@dataclass
class WebhookDelivery:
    delivery_id: str
    subscription_id: str
    event_type: str
    payload: dict[str, Any]
    status: str = "pending"
    attempts: int = 0
    max_retries: int = 3
    last_error: str | None = None
    delivered_at: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "delivery_id": self.delivery_id,
            "subscription_id": self.subscription_id,
            "event_type": self.event_type,
            "payload": self.payload,
            "status": self.status,
            "attempts": self.attempts,
            "max_retries": self.max_retries,
            "last_error": self.last_error,
            "delivered_at": self.delivered_at,
            "created_at": self.created_at,
        }


class WebhookRegistry:
    def __init__(self) -> None:
        self._subscriptions: dict[str, WebhookSubscription] = {}
        self._deliveries: list[WebhookDelivery] = []

    def subscribe(
        self,
        *,
        url: str,
        event_types: list[str],
        secret: str | None = None,
    ) -> WebhookSubscription:
        sub = WebhookSubscription(
            subscription_id=str(uuid.uuid4()),
            url=url,
            event_types=list(event_types),
            secret=secret or secrets.token_urlsafe(32),
        )
        self._subscriptions[sub.subscription_id] = sub
        return sub

    def list_subscriptions(self) -> list[WebhookSubscription]:
        return list(self._subscriptions.values())

    def get_subscription(self, subscription_id: str) -> WebhookSubscription | None:
        return self._subscriptions.get(subscription_id)

    def enqueue_delivery(
        self,
        *,
        event_type: str,
        payload: dict[str, Any],
    ) -> list[WebhookDelivery]:
        created: list[WebhookDelivery] = []
        for sub in self._subscriptions.values():
            if not sub.active:
                continue
            if event_type not in sub.event_types and "*" not in sub.event_types:
                continue
            delivery = WebhookDelivery(
                delivery_id=str(uuid.uuid4()),
                subscription_id=sub.subscription_id,
                event_type=event_type,
                payload={
                    **payload,
                    "subscription_id": sub.subscription_id,
                    "event_type": event_type,
                },
                max_retries=sub.max_retries,
            )
            self._deliveries.append(delivery)
            created.append(delivery)
        return created

    def deliver_pending(self) -> dict[str, Any]:
        """Stub delivery — marks as delivered or retries on failure."""
        delivered = 0
        failed = 0
        retried = 0
        for d in self._deliveries:
            if d.status == "delivered":
                continue
            sub = self._subscriptions.get(d.subscription_id)
            if not sub or not sub.active:
                d.status = "skipped"
                continue
            d.attempts += 1
            unreachable = sub.url.startswith("http://invalid.")
            if unreachable:
                if d.attempts < d.max_retries:
                    d.status = "retry"
                    retried += 1
                else:
                    d.status = "failed"
                    d.last_error = "max_retries_exceeded"
                    failed += 1
            else:
                d.status = "delivered"
                d.delivered_at = datetime.now(timezone.utc).isoformat()
                delivered += 1
        return {
            "ok": True,
            "delivered": delivered,
            "failed": failed,
            "retried": retried,
            "pending": sum(1 for d in self._deliveries if d.status in ("pending", "retry")),
        }

    def list_deliveries(self, *, limit: int = 50) -> list[dict[str, Any]]:
        return [d.to_dict() for d in self._deliveries[-limit:]]


_registry: WebhookRegistry | None = None


def get_webhook_registry() -> WebhookRegistry:
    global _registry
    if _registry is None:
        _registry = WebhookRegistry()
    return _registry


def reset_webhook_registry() -> None:
    global _registry
    _registry = None


def supported_webhook_event_types() -> list[str]:
    return [e.value for e in WebhookEventType]
