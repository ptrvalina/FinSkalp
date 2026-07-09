"""Публичные обозреватели блокчейна (TronScan, Ethplorer)."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.osint_core.open_source_collector import (
    OpenMentionHit,
    _eth_public_intel,
    _is_real_tron_address,
    _looks_like_btc,
    _tronscan_intel,
)
from flowsint_crypto_compliance.osint_core.scalpel.collector_base import (
    CollectorResult,
    ScalpelCollector,
)
from flowsint_types.fiat_crypto import Chain


class BlockchainExplorerCollector(ScalpelCollector):
    collector_id = "blockchain_explorer"
    name_ru = "Публичные обозреватели on-chain"
    inspired_by = "Etherscan / TronScan / Blockchair patterns"

    async def collect(
        self,
        address: str,
        chain: Chain,
        *,
        counterparties: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> CollectorResult:
        timeout = self._gw.config.timeout_sec
        hits: list[OpenMentionHit] = []
        status = "miss"
        detail = ""

        if chain == Chain.TRON and _is_real_tron_address(address):
            hits, detail = await _tronscan_intel(address, timeout)
            status = "ok" if hits else detail
        elif chain == Chain.ETH and address.startswith("0x") and len(address) >= 42:
            hits, detail = await _eth_public_intel(address, timeout)
            status = "ok" if hits else detail
        elif chain == Chain.BTC and _looks_like_btc(address):
            status = "corpus_only"
            detail = "btc_explorer_deferred"

        return CollectorResult(
            collector_id=self.collector_id,
            hits=hits,
            status="ok" if hits else "miss",
            detail=detail or status,
        )
