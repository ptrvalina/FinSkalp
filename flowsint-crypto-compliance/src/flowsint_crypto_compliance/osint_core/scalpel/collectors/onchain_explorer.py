"""#1 On-chain Explorer — live TronGrid + mempool.space."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.osint_core.live_collectors import (
    collect_btc_chain,
    collect_tron_chain,
    collect_tron_trc20_transfers,
)
from flowsint_crypto_compliance.osint_core.scalpel.collector_base import (
    CollectorResult,
    ScalpelCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.live_collector_bridge import (
    hits_from_btc,
    hits_from_trc20,
    hits_from_tron_chain,
)
from flowsint_crypto_compliance.osint_core.scalpel.rate_limit import acquire
from flowsint_types.fiat_crypto import Chain


class OnchainExplorerCollector(ScalpelCollector):
    collector_id = "onchain_explorer"
    name_ru = "On-chain Explorer (live)"
    legal_basis_ru = "TronGrid, mempool.space — live API"
    inspired_by = "TronGrid / mempool.space"

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

        hits: list = []
        details: list[str] = []
        entities: dict[str, Any] = {}
        if chain == Chain.TRON and address.startswith("T") and len(address) >= 30:
            trx = await collect_tron_chain(address)
            trc20 = await collect_tron_trc20_transfers(address)
            hits.extend(hits_from_tron_chain(trx, address))
            hits.extend(hits_from_trc20(trc20, address))
            details.append(f"trx:{trx.get('tx_count', 0)};trc20:{trc20.get('transfer_count', 0)}")
            entities = {
                "counterparties": list(
                    dict.fromkeys(
                        (trx.get("counterparties") or []) + (trc20.get("counterparties") or [])
                    )
                )[:30],
                "transfers": (trc20.get("transfers") or [])[:20],
            }
        elif chain == Chain.BTC and address.startswith(("1", "3", "bc1")):
            btc = await collect_btc_chain(address)
            hits.extend(hits_from_btc(btc, address))
            details.append(f"btc_tx:{btc.get('tx_count', 0)}")
            entities = {
                "counterparties": btc.get("counterparties") or [],
                "transfers": btc.get("transfers") or [],
            }
        else:
            return CollectorResult(collector_id=self.collector_id, hits=[], status="miss")

        return CollectorResult(
            collector_id=self.collector_id,
            hits=hits,
            status="ok" if hits else "miss",
            detail=";".join(details),
            entities=entities if hits else {},
        )
