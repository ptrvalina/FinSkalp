"""Maigret full scan (3000+ sites) — Celery или sync."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.osint_core.open_source_collector import OpenMentionHit
from flowsint_crypto_compliance.osint_core.scalpel.collector_base import (
    CollectorResult,
    ScalpelCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.workers.maigret_runner import (
    hits_from_maigret_result,
    maigret_available,
    run_maigret,
)
from flowsint_types.fiat_crypto import Chain


class MaigretExtCollector(ScalpelCollector):
    collector_id = "maigret_ext"
    name_ru = "Maigret · 3000+ площадок"
    inspired_by = "soxoj/maigret"

    async def collect(
        self,
        address: str,
        chain: Chain,
        *,
        counterparties: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> CollectorResult:
        usernames = _usernames(address, context)
        if not usernames:
            return CollectorResult(
                collector_id=self.collector_id,
                hits=[],
                status="skip",
                detail="no_usernames",
            )

        all_hits: list[OpenMentionHit] = []
        details: list[str] = []
        for username in usernames[:2]:
            result = run_maigret(username, use_tor=bool(self._gw.config.tor_enabled()))
            details.append(f"{username}:{result.get('status')}")
            hits = hits_from_maigret_result(
                result, address=address, chain=chain.value
            )
            all_hits.extend(hits)

        engine = "maigret_cli" if maigret_available() else "maigret_missing"
        return CollectorResult(
            collector_id=self.collector_id,
            hits=all_hits,
            status="ok" if all_hits else ("miss" if maigret_available() else "disabled"),
            detail=f"{engine};" + ";".join(details),
        )


def _usernames(address: str, context: dict[str, Any] | None) -> list[str]:
    out: list[str] = []
    if context:
        for u in context.get("usernames") or []:
            u = str(u).lstrip("@")
            if u and u not in out:
                out.append(u)
        for m in context.get("mentions") or []:
            for token in (m.get("excerpt_ru") or "").split():
                if token.startswith("@") and len(token) > 2:
                    out.append(token[1:].strip(".,;"))
    if address.startswith("TRU_") or "_" in address[:10]:
        slug = address.split("_")[-1].lower()[:20]
        if slug and f"otc_{slug}" not in out:
            out.append(f"otc_{slug}")
    return out[:3]
