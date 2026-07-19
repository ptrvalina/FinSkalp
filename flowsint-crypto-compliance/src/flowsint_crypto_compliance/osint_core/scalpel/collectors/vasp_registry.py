"""Реестр VASP СНГ — match по кошельку и по юридическому имени."""

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
from flowsint_crypto_compliance.osint_core.scalpel.seed_query import bare_seed_query, seed_kind
from flowsint_crypto_compliance.registry.cis_vasp_registry import match_vasp_by_name
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
        kind = seed_kind(address)
        query = bare_seed_query(address)

        # Org / person name seeds: search CIS VASP registry by legal name
        if kind in {"org", "person", "unknown"} and query and not hits:
            for entity in match_vasp_by_name(query):
                risk = entity.get("risk", "medium")
                if risk not in ("severe", "high", "medium", "low"):
                    risk = "medium"
                conf = {"severe": 0.78, "high": 0.68, "medium": 0.58, "low": 0.48}[risk]
                licensed = entity.get("licensed", True)
                hits.append(
                    OpenMentionHit(
                        source_type="otc_board",
                        source_name=f"{entity.get('regulator', 'СНГ')} · {entity['id']}",
                        title_ru=f"Реестр VASP СНГ: {entity['legal_name_ru']}",
                        excerpt_ru=(
                            f"Совпадение по имени «{query}». "
                            f"Юрисдикция {entity.get('jurisdiction')}, "
                            f"тип «{entity.get('license_type')}», "
                            f"статус {entity.get('status')}."
                        ),
                        url=entity.get("registry_source") or entity.get("website"),
                        risk_tag="licensed_vasp" if licensed else "otc_exchange",
                        confidence=conf,
                        address=address,
                        chain=chain.value,
                    )
                )

        return CollectorResult(
            collector_id=self.collector_id,
            hits=hits,
            status="ok" if hits else "miss",
            detail=f"hits:{len(hits)};kind:{kind}",
        )
