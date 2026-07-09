from typing import Any, Dict, List, Optional

from flowsint_core.core.enricher_base import Enricher
from flowsint_crypto_compliance.engine.clusterer import ClusterEngine
from flowsint_crypto_compliance.engine.region_profiler import RegionProfiler
from flowsint_enrichers.registry import flowsint_enricher
from flowsint_types.fiat_crypto import CryptoCluster, LicensedPlatformEvent
from flowsint_types.wallet import CryptoWallet


@flowsint_enricher
class WalletToClusterProfile(Enricher):
    """[REG] Resolve wallet to probabilistic cluster and regional affinity profile."""

    InputType = CryptoWallet
    OutputType = CryptoCluster

    @classmethod
    def name(cls) -> str:
        return "wallet_to_cluster_profile"

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
            "Builds a probabilistic cluster around a wallet using co-occurrence with "
            "licensed-platform and control-purchase seeds in the investigation."
        )

    async def scan(self, data: List[InputType]) -> List[OutputType]:
        # MVP placeholder: returns singleton cluster per address until sketch context wired
        results: List[OutputType] = []
        engine = ClusterEngine()
        profiler = RegionProfiler()

        licensed: list[LicensedPlatformEvent] = []
        engine.ingest_licensed_events(licensed)

        for wallet in data:
            chain = _guess_chain(wallet.address)
            engine.ingest_counterparty_links(chain, wallet.address, [])
            clusters = engine.build_clusters(min_confidence=0.2)
            if clusters:
                cluster = profiler.apply_to_cluster(clusters[0], chain)
            else:
                from flowsint_types.fiat_crypto import EntityKind, EvidenceSource

                cluster = CryptoCluster(
                    cluster_id=f"{chain.value}_singleton_{wallet.address[:8]}",
                    label="unclustered_wallet",
                    entity_kind=EntityKind.UNKNOWN,
                    confidence=0.2,
                    member_addresses=[wallet.address],
                    evidence_sources=[EvidenceSource.BLOCKCHAIN],
                )
            results.append(cluster)
        return results

    def postprocess(
        self, results: List[OutputType], original_input: List[InputType]
    ) -> List[OutputType]:
        if not self._graph_service:
            return results

        for cluster in results:
            self.create_node(cluster)
            for addr in cluster.member_addresses or []:
                wallet = CryptoWallet(address=addr)
                self.create_node(wallet)
                self.create_relationship(wallet, cluster, "MEMBER_OF")
        return results

    @classmethod
    def get_params_schema(cls) -> List[Dict[str, Any]]:
        return []


def _guess_chain(address: str):
    from flowsint_types.fiat_crypto import Chain

    if address.startswith("0x") and len(address) == 42:
        return Chain.ETH
    if address.startswith("T") and len(address) == 34:
        return Chain.TRON
    return Chain.BTC


InputType = WalletToClusterProfile.InputType
OutputType = WalletToClusterProfile.OutputType
