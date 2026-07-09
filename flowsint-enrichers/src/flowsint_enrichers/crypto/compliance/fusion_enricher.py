from typing import Any, Dict, List, Optional

from flowsint_core.core.enricher_base import Enricher
from flowsint_crypto_compliance.chains import get_chain_adapter
from flowsint_crypto_compliance.ingestion.pipeline import IngestPipeline
from flowsint_enrichers.registry import flowsint_enricher
from flowsint_types.fiat_crypto import Chain, FusedAttribution
from flowsint_types.wallet import CryptoWallet


@flowsint_enricher
class WalletToFusedAttribution(Enricher):
    """[REG/OSINT] Full fusion: sovereign engine + sovereign registry + bank linkage."""

    InputType = CryptoWallet
    OutputType = FusedAttribution

    @classmethod
    def name(cls) -> str:
        return "wallet_to_fused_attribution"

    @classmethod
    def category(cls) -> str:
        return "Compliance"

    @classmethod
    def key(cls) -> str:
        return "address"

    @classmethod
    def icon(cls) -> str | None:
        return "cryptowallet"

    @classmethod
    def documentation(cls) -> str:
        return (
            "Runs OSINT fusion core for a wallet: merges domestic regulator signals, "
            "the sovereign RF/CIS risk-label registry, clustering and bank↔crypto linkage."
        )

    async def scan(self, data: List[InputType]) -> List[OutputType]:
        from flowsint_crypto_compliance.osint_core.fusion_engine import InvestigationBundle

        params = self.get_params()
        case_id = params.get("case_id", self.sketch_id or "default-case")

        adapters = {
            Chain.BTC: get_chain_adapter(Chain.BTC),
            Chain.ETH: get_chain_adapter(Chain.ETH),
            Chain.TRON: get_chain_adapter(Chain.TRON),
        }
        pipeline = IngestPipeline()
        pipeline.engine._adapters = adapters  # extend engine with chain adapters

        bundle = InvestigationBundle(case_id=case_id)
        result = await pipeline.engine.fuse(bundle)

        address_set = {w.address for w in data}
        return [a for a in result.attributions if a.address in address_set]

    def postprocess(
        self, results: List[OutputType], original_input: List[InputType]
    ) -> List[OutputType]:
        if not self._graph_service:
            return results

        params = self.get_params()
        case_ref = params.get("case_ref") or params.get("case_id") or self.sketch_id

        for attr in results:
            self.create_node(attr)
            wallet = next((w for w in original_input if w.address == attr.address), None)
            if wallet:
                self.create_node(wallet)
                self.create_relationship(wallet, attr, "FUSED_ATTRIBUTION")

        if case_ref and results:
            try:
                from flowsint_crypto_compliance.osint_core.evidence_graph import (
                    EvidenceGraph,
                    NodeKind,
                )
                from flowsint_crypto_compliance.storage.neo4j_pivots import (
                    ComplianceNeo4jPivotExporter,
                )

                graph = EvidenceGraph()
                for attr in results:
                    graph.upsert_node(
                        kind=NodeKind.WALLET,
                        primary_key=f"{attr.chain.value}:{attr.address}",
                        confidence=attr.confidence,
                        region=attr.primary_region,
                    )
                ComplianceNeo4jPivotExporter().export(graph, case_ref=str(case_ref))
            except Exception:
                pass

        return results

    @classmethod
    def get_params_schema(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "case_id",
                "type": "string",
                "description": "Regulator case ID for evidence graph scope.",
                "required": False,
            },
        ]


InputType = WalletToFusedAttribution.InputType
OutputType = WalletToFusedAttribution.OutputType
