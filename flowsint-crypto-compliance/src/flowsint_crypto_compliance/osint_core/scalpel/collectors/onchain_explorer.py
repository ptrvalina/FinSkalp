"""#1 On-chain Explorer — live TronGrid + Etherscan + BscScan + mempool.space + Blockscout."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.osint_core.live_collectors import (
    collect_bsc_chain,
    collect_btc_chain,
    collect_eth_chain,
    collect_polygon_chain,
    collect_tron_chain,
    collect_tron_trc20_transfers,
)
from flowsint_crypto_compliance.osint_core.scalpel.collector_base import (
    CollectorResult,
    ScalpelCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.live_collector_bridge import (
    hits_from_btc,
    hits_from_evm,
    hits_from_trc20,
    hits_from_tron_chain,
)
from flowsint_crypto_compliance.osint_core.scalpel.rate_limit import acquire
from flowsint_types.fiat_crypto import Chain


class OnchainExplorerCollector(ScalpelCollector):
    collector_id = "onchain_explorer"
    name_ru = "On-chain Explorer (live)"
    legal_basis_ru = "TronGrid, Etherscan, BscScan, Blockscout, mempool.space — live API"
    inspired_by = "TronGrid / Etherscan / mempool.space"

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
                )[:40],
                "transfers": ((trx.get("transfers") or []) + (trc20.get("transfers") or []))[:40],
            }
        elif chain == Chain.BTC and address.startswith(("1", "3", "bc1")):
            btc = await collect_btc_chain(address)
            hits.extend(hits_from_btc(btc, address))
            details.append(f"btc_tx:{btc.get('tx_count', 0)}")
            entities = {
                "counterparties": btc.get("counterparties") or [],
                "transfers": btc.get("transfers") or [],
            }
        elif chain == Chain.ETH and address.startswith("0x") and len(address) >= 40:
            eth = await collect_eth_chain(address)
            hits.extend(hits_from_evm(eth, address, chain="eth", explorer="etherscan"))
            details.append(f"eth_tx:{eth.get('tx_count', 0)};token:{eth.get('token_tx_count', 0)}")
            entities = {
                "counterparties": eth.get("counterparties") or [],
                "transfers": eth.get("transfers") or [],
            }
        elif chain == Chain.BSC and address.startswith("0x") and len(address) >= 40:
            bsc = await collect_bsc_chain(address)
            hits.extend(hits_from_evm(bsc, address, chain="bsc", explorer="bscscan"))
            details.append(f"bsc_tx:{bsc.get('tx_count', 0)}")
            entities = {
                "counterparties": bsc.get("counterparties") or [],
                "transfers": bsc.get("transfers") or [],
            }
        elif chain == Chain.POLYGON and address.startswith("0x") and len(address) >= 40:
            poly = await collect_polygon_chain(address)
            hits.extend(hits_from_evm(poly, address, chain="polygon", explorer="blockscout"))
            details.append(f"polygon_tx:{poly.get('tx_count', 0)}")
            entities = {
                "counterparties": poly.get("counterparties") or [],
                "transfers": poly.get("transfers") or [],
            }
        else:
            return CollectorResult(collector_id=self.collector_id, hits=[], status="miss")

        return CollectorResult(
            collector_id=self.collector_id,
            hits=hits,
            status="ok" if hits else "miss",
            detail=";".join(details),
            entities=entities if (hits or entities.get("counterparties")) else {},
        )
