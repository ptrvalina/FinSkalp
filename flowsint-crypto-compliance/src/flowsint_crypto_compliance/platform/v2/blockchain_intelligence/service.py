"""RFC-0012 Ch.5, 13–14 — blockchain intelligence service."""

from __future__ import annotations

import os
import time
import uuid
from typing import Any

from flowsint_crypto_compliance.platform.v2.blockchain_intelligence.analytics import (
    behavior_profile,
    build_flow_graph,
    cluster_counterparties,
    enrich_neighborhood_from_index,
    normalize_transfers,
    profile_address,
)
from flowsint_crypto_compliance.platform.v2.blockchain_intelligence.canonical_model import PIPELINE_STAGES
from flowsint_crypto_compliance.platform.v2.events import EventType, PlatformEvent
from flowsint_crypto_compliance.platform.v2.event_bus import get_platform_event_bus
from flowsint_crypto_compliance.platform.v2.intelligence.blockchain_capabilities import (
    get_chain_adapter_by_key,
    normalize_chain_key,
)

_service: "BlockchainIntelligenceService | None" = None


def default_tenant_id() -> uuid.UUID:
    return uuid.UUID(os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001"))


class BlockchainIntelligenceService:
    """Unified blockchain analysis — adapters → canonical model → KG events."""

    async def analyze_address(
        self,
        *,
        address: str,
        chain: str,
        case_ref: str | None = None,
        tenant_id: uuid.UUID | None = None,
        depth: int = 1,
        limit: int = 50,
        publish: bool = True,
        use_memory: bool | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        tid = tenant_id or default_tenant_id()
        chain_key = normalize_chain_key(chain)
        memory = use_memory if use_memory is not None else os.getenv("FINSKALP_ENTITY_STORE", "").lower() in (
            "memory",
            "in_memory",
        )

        stages_completed: list[str] = []
        errors: list[str] = []

        adapter = get_chain_adapter_by_key(chain_key, use_memory=memory)
        if adapter is None:
            return {
                "ok": False,
                "message_ru": f"Сеть {chain_key} не поддерживается",
                "chain": chain_key,
            }

        stages_completed.append("source")
        stages_completed.append("adapter")

        try:
            neighborhood = await adapter.get_neighborhood(address, depth=depth, limit=limit)
        except Exception as exc:
            errors.append(str(exc))
            from flowsint_crypto_compliance.chains.base import AddressNeighborhood, InMemoryChainAdapter
            from flowsint_types.fiat_crypto import Chain

            meta_chain = Chain.TRON if chain_key == "tron" else Chain.ETH
            adapter = InMemoryChainAdapter(meta_chain, [])
            neighborhood = await adapter.get_neighborhood(address, depth=depth, limit=limit)

        neighborhood, data_source, indexed_count = enrich_neighborhood_from_index(
            neighborhood, chain_key, address
        )

        canonical_transfers = normalize_transfers(neighborhood, chain_key)
        stages_completed.extend(["normalizer", "validator"])

        profile = profile_address(neighborhood)
        clusters = cluster_counterparties(neighborhood)
        flow_graph = build_flow_graph(neighborhood, depth=depth)
        behavior = behavior_profile(profile, neighborhood)
        stages_completed.extend(["entity_resolution", "knowledge_graph"])

        explain = {
            "transactions_used": len(canonical_transfers),
            "rules_triggered": behavior.get("anomalies") or [],
            "sources": [f"adapter:{chain_key}"] + ([f"local_index:{indexed_count}"] if indexed_count else []),
            "data_source": data_source,
            "indexed_transfers": indexed_count,
            "limitations_ru": "Анализ ограничен глубиной neighborhood и доступностью провайдера",
            "clustering_methods": [c["method"] for c in clusters[:5]],
        }

        entity_id = None
        if publish and case_ref:
            from flowsint_crypto_compliance.platform.v2.ingest_pipeline import get_ingest_pipeline

            ing = get_ingest_pipeline().ingest(
                tenant_id=tid,
                source_type="blockchain_intelligence",
                entity_type="blockchain_address",
                entity_value=address,
                chain=chain_key,
                case_ref=case_ref,
                confidence=0.7,
                payload={
                    "profile": profile,
                    "behavior": behavior,
                    "clusters": clusters,
                    "explain": explain,
                },
                require_relation_evidence=False,
            )
            if ing.ok:
                entity_id = str(ing.entity_id) if ing.entity_id else None
                stages_completed.extend(ing.stages_completed)
            else:
                errors.extend(ing.errors)

        stages_completed.extend(["risk_engine", "timeline"])

        bus = get_platform_event_bus()
        bus.publish(
            PlatformEvent(
                event_type=EventType.WALLET_OPENED,
                source="blockchain_intelligence.analyze",
                tenant_id=tid,
                payload={
                    "address": address,
                    "chain": chain_key,
                    "case_ref": case_ref,
                    "ui_event": "WalletOpened",
                },
            )
        )

        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return {
            "ok": True,
            "address": address,
            "chain": chain_key,
            "case_ref": case_ref,
            "entity_id": entity_id,
            "profile": profile,
            "behavior": behavior,
            "clusters": clusters,
            "flow_graph": flow_graph,
            "canonical_transfers": canonical_transfers[:limit],
            "pipeline": {
                "stages": PIPELINE_STAGES,
                "stages_completed": stages_completed,
                "errors": errors,
            },
            "explain": explain,
            "metrics": {
                "transactions_processed": len(canonical_transfers),
                "latency_ms": latency_ms,
                "source_availability": len(errors) == 0,
            },
            "latency_ms": latency_ms,
        }


def get_blockchain_intelligence_service() -> BlockchainIntelligenceService:
    global _service
    if _service is None:
        _service = BlockchainIntelligenceService()
    return _service
