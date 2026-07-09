"""Watchlist / sanctions subscription monitoring."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from flowsint_crypto_compliance.infrastructure.compliance_events import get_event_bus
from flowsint_crypto_compliance.storage.db_models import ComplianceWatchlistSubscription


async def _check_address_sanctions(address: str) -> dict[str, Any]:
    from flowsint_crypto_compliance.osint_core.live_collectors import collect_sanctions

    return await collect_sanctions(address)


def _has_sanction_hit(data: dict[str, Any]) -> bool:
    body = data.get("data") or data
    if isinstance(body, dict):
        results = body.get("results") or body.get("data", {}).get("results")
        if results:
            return len(results) > 0
    return False


class WatchlistMonitorService:
    def __init__(self, db: Session):
        self._db = db

    def subscribe(
        self,
        owner_id: uuid.UUID,
        *,
        address: str,
        chain: str = "tron",
        label: str | None = None,
    ) -> ComplianceWatchlistSubscription:
        existing = (
            self._db.query(ComplianceWatchlistSubscription)
            .filter(
                ComplianceWatchlistSubscription.owner_id == owner_id,
                ComplianceWatchlistSubscription.address == address.strip(),
                ComplianceWatchlistSubscription.chain == chain.lower(),
            )
            .first()
        )
        if existing:
            existing.active = True
            if label:
                existing.label = label
            self._db.commit()
            self._db.refresh(existing)
            return existing
        sub = ComplianceWatchlistSubscription(
            owner_id=owner_id,
            address=address.strip(),
            chain=chain.lower(),
            label=label,
            active=True,
        )
        self._db.add(sub)
        self._db.commit()
        self._db.refresh(sub)
        return sub

    def list_subscriptions(self, owner_id: uuid.UUID) -> list[ComplianceWatchlistSubscription]:
        return (
            self._db.query(ComplianceWatchlistSubscription)
            .filter(ComplianceWatchlistSubscription.owner_id == owner_id, ComplianceWatchlistSubscription.active.is_(True))
            .order_by(ComplianceWatchlistSubscription.created_at.desc())
            .all()
        )

    async def scan_subscription(self, sub_id: uuid.UUID) -> dict[str, Any] | None:
        sub = self._db.get(ComplianceWatchlistSubscription, sub_id)
        if not sub or not sub.active:
            return None
        data = await _check_address_sanctions(sub.address)
        sub.last_checked_at = datetime.now(timezone.utc)
        hit = _has_sanction_hit(data)
        if hit:
            sub.last_hit_at = sub.last_checked_at
            sub.last_hit_payload = {"source": "opensanctions", "snapshot": data}
            get_event_bus().publish(
                "watchlist_sanction_hit",
                payload={
                    "address": sub.address,
                    "chain": sub.chain,
                    "label": sub.label,
                    "subscription_id": str(sub.id),
                },
                severity="critical",
                text_ru=f"Санкции · {sub.address[:12]}… попал в новый список",
            )
        self._db.commit()
        return {"subscription_id": str(sub.id), "hit": hit, "checked_at": sub.last_checked_at.isoformat()}

    async def scan_all_active(self, limit: int = 200) -> dict[str, Any]:
        subs = (
            self._db.query(ComplianceWatchlistSubscription)
            .filter(ComplianceWatchlistSubscription.active.is_(True))
            .limit(limit)
            .all()
        )
        hits = 0
        for sub in subs:
            out = await self.scan_subscription(sub.id)
            if out and out.get("hit"):
                hits += 1
            await asyncio.sleep(0.2)
        return {"scanned": len(subs), "hits": hits}
