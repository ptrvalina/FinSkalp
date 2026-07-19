"""#3 Username/Social — live Maigret."""

from __future__ import annotations

import os
from typing import Any

from flowsint_crypto_compliance.osint_core.live_collectors import collect_maigret
from flowsint_crypto_compliance.osint_core.scalpel.collector_base import (
    CollectorResult,
    ScalpelCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.live_collector_bridge import hits_from_maigret
from flowsint_crypto_compliance.osint_core.scalpel.rate_limit import acquire
from flowsint_crypto_compliance.osint_core.scalpel.seed_query import (
    bare_seed_query,
    person_to_usernames,
    seed_kind,
)
from flowsint_types.fiat_crypto import Chain


class UsernameSocialCollector(ScalpelCollector):
    collector_id = "username_social"
    name_ru = "Username / Maigret (live)"
    legal_basis_ru = "Maigret — live scan 500+ публичных площадок"
    inspired_by = "Maigret"

    async def collect(
        self,
        address: str,
        chain: Chain,
        *,
        counterparties: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> CollectorResult:
        if not acquire(self.collector_id):
            return CollectorResult(
                collector_id=self.collector_id, hits=[], status="rate_limited"
            )

        usernames = _usernames(address, context)
        hits = []
        errors = 0
        max_users = int(os.getenv("FINSKALP_MAIGRET_USERNAMES", "1"))
        for username in usernames[: max(1, max_users)]:
            try:
                data = await collect_maigret(username)
                hits.extend(hits_from_maigret(data, address, chain.value))
            except ValueError:
                errors += 1
            except Exception:
                errors += 1

        return CollectorResult(
            collector_id=self.collector_id,
            hits=hits,
            status="ok" if hits else "miss",
            detail=f"usernames:{len(usernames)};hits:{len(hits)};errors:{errors}",
        )


def _usernames(address: str, context: dict[str, Any] | None) -> list[str]:
    out: list[str] = []
    if context:
        for u in context.get("usernames") or []:
            u = str(u).lstrip("@").strip()
            if u and u not in out:
                out.append(u)

    kind = seed_kind(address)
    bare = bare_seed_query(address)
    if kind == "person" or (kind == "unknown" and " " in bare):
        for u in person_to_usernames(bare):
            if u not in out:
                out.append(u)
    elif kind == "user" and bare and bare not in out:
        out.append(bare)

    return out[:6]
