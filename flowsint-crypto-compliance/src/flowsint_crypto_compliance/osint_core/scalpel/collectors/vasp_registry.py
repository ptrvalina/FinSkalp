"""Реестр VASP СНГ."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.osint_core.open_source_collector import (
    OpenMentionHit,
    _search_otc_registry,
)
from flowsint_crypto_compliance.osint_core.scalpel.collector_base import (
    CollectorResult,
    ScalpelCollector,
)
from flowsint_types.fiat_crypto import Chain


class VaspRegistryCollector(ScalpelCollector):
    collector_id = "vasp_registry"
    name_ru = "Реестр VASP СНГ"
    legal_basis_ru = "ЦБ РФ, NAPP (KZ), AFSA, ПВТ Беларусь — официальные публичные реестры"
    inspired_by = "ЦБ РФ CFA OIS · NAPP · AFSA"

    async def collect(
        self,
        address: str,
        chain: Chain,
        *,
        counterparties: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> CollectorResult:
        hits = _search_otc_registry(address, chain)
        return CollectorResult(collector_id=self.collector_id, hits=hits)
