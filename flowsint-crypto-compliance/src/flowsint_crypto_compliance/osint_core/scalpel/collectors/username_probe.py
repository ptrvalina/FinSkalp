"""
Username probe — облегчённый аналог Maigret/Sherlock.

Проверяет публичные профили по никнеймам, извлечённым из OSINT-контекста.
Полный Maigret (3000+ сайтов) подключается опционально через CLI-обёртку.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flowsint_crypto_compliance.osint_core.open_source_collector import OpenMentionHit
from flowsint_crypto_compliance.osint_core.scalpel.collector_base import (
    CollectorResult,
    ScalpelCollector,
)
from flowsint_types.fiat_crypto import Chain

_SITES_PATH = Path(__file__).resolve().parents[3] / "data" / "username_probe_sites.json"


class UsernameProbeCollector(ScalpelCollector):
    collector_id = "username_probe"
    name_ru = "Username OSINT (Maigret/Sherlock паттерн)"
    inspired_by = "Maigret + Sherlock"

    async def collect(
        self,
        address: str,
        chain: Chain,
        *,
        counterparties: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> CollectorResult:
        usernames = _usernames_from_context(address, context)
        if not usernames:
            return CollectorResult(
                collector_id=self.collector_id,
                hits=[],
                status="skip",
                detail="no_usernames",
            )

        sites = _load_sites()
        hits: list[OpenMentionHit] = []
        checked = 0

        for username in usernames[:3]:
            for site in sites[:12]:
                url = site["url"].format(username=username)
                checked += 1
                code, body, _ = await self._gw.fetch(url, route="clearnet", method="GET")
                if code not in (200, 301, 302):
                    continue
                marker = site.get("exists_marker", username)
                missing = site.get("missing_marker", "")
                if missing and missing in body:
                    continue
                if marker in body or code == 200:
                    hits.append(
                        OpenMentionHit(
                            source_type="username",
                            source_name=site["name"],
                            title_ru=f"Профиль @{username} на {site['name']}",
                            excerpt_ru=(
                                f"Username OSINT: ник «{username}» обнаружен на "
                                f"{site['name']} (паттерн Maigret/Sherlock)."
                            ),
                            url=url,
                            risk_tag=site.get("tag", "social_profile"),
                            confidence=float(site.get("confidence", 0.55)),
                            address=address,
                            chain=chain.value,
                        )
                    )
                    break

        return CollectorResult(
            collector_id=self.collector_id,
            hits=hits,
            status="ok" if hits else "miss",
            detail=f"checked:{checked}",
        )


def _usernames_from_context(address: str, context: dict[str, Any] | None) -> list[str]:
    out: list[str] = []
    if context:
        for u in context.get("usernames") or []:
            if u and u not in out:
                out.append(str(u).lstrip("@"))
        for m in context.get("mentions") or []:
            ex = (m.get("excerpt_ru") or "") + " " + (m.get("title_ru") or "")
            if "@" in ex:
                for part in ex.split():
                    if part.startswith("@") and len(part) > 2:
                        out.append(part[1:].strip(".,;"))
    if address.startswith("TRU_") or "_" in address[:8]:
        slug = address.split("_")[-1].lower()[:16]
        if slug and slug not in out:
            out.append(f"otc_{slug}")
    return out[:5]


def _load_sites() -> list[dict[str, Any]]:
    if _SITES_PATH.is_file():
        return json.loads(_SITES_PATH.read_text(encoding="utf-8"))
    return [
        {
            "name": "GitHub",
            "url": "https://github.com/{username}",
            "exists_marker": "pinned-items",
            "missing_marker": "Not Found",
            "confidence": 0.72,
            "tag": "dev_profile",
        },
        {
            "name": "Reddit",
            "url": "https://www.reddit.com/user/{username}",
            "exists_marker": "Reddit",
            "missing_marker": "Sorry, nobody on Reddit goes by that name",
            "confidence": 0.60,
            "tag": "forum_profile",
        },
    ]
