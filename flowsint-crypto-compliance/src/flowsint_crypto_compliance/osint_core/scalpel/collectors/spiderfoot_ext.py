"""SpiderFoot module runner — 200+ OSINT модулей."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.osint_core.scalpel.collector_base import (
    CollectorResult,
    ScalpelCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.workers.spiderfoot_runner import (
    hits_from_spiderfoot_result,
    run_spiderfoot,
    spiderfoot_available,
)
from flowsint_types.fiat_crypto import Chain


class SpiderFootExtCollector(ScalpelCollector):
    collector_id = "spiderfoot_ext"
    name_ru = "SpiderFoot · автоматизация OSINT"
    inspired_by = "smicallef/spiderfoot"

    async def collect(
        self,
        address: str,
        chain: Chain,
        *,
        counterparties: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> CollectorResult:
        targets = _targets_for_scan(address, chain, context)
        if not targets:
            return CollectorResult(
                collector_id=self.collector_id,
                hits=[],
                status="skip",
                detail="no_targets",
            )

        all_hits = []
        details: list[str] = []
        for target in targets[:2]:
            result = run_spiderfoot(target)
            details.append(f"{target[:20]}:{result.get('status')}")
            all_hits.extend(
                hits_from_spiderfoot_result(
                    result, address=address, chain=chain.value
                )
            )

        return CollectorResult(
            collector_id=self.collector_id,
            hits=all_hits,
            status="ok" if all_hits else "miss",
            detail=(
                ("spiderfoot_cli" if spiderfoot_available() else "spiderfoot_compat")
                + ";"
                + ";".join(details)
            ),
        )


def _targets_for_scan(
    address: str, chain: Chain, context: dict[str, Any] | None
) -> list[str]:
    targets: list[str] = [address]
    if context:
        for m in context.get("mentions") or []:
            url = m.get("url")
            if url and url.startswith("http"):
                targets.append(url)
    if address.startswith("0x"):
        targets.append(address)
    elif address.startswith("T") and len(address) > 30:
        targets.append(address)
    return list(dict.fromkeys(targets))[:3]
