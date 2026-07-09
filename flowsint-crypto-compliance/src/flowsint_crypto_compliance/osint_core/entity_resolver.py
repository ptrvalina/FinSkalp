from __future__ import annotations

from flowsint_types.fiat_crypto import (
    BankRegulatorFeed,
    Chain,
    ControlPurchaseEvent,
    EvidenceSource,
    FiatLegEvent,
    LicensedPlatformEvent,
    SovereignRiskLabel,
)

from .evidence_graph import EvidenceGraph, NodeKind


class EntityResolver:
    """
    Resolve and link entities across bank, regulator, platform and registry sources.

    Creates strong edges:
      bank → subject → wallet
      bank → platform → wallet
      bank → wallet (direct if address reported)
    """

    def __init__(self, graph: EvidenceGraph) -> None:
        self._graph = graph

    def ingest_bank_feed(self, feed: BankRegulatorFeed) -> None:
        bank_node = self._graph.upsert_node(
            kind=NodeKind.BANK_FEED,
            primary_key=feed.feed_id,
            payload=feed.model_dump(),
            source=EvidenceSource.BANK_REGULATOR_HUB,
            region=feed.region,
            confidence=0.95,
        )

        if feed.subject_id:
            subject = self._graph.upsert_node(
                kind=NodeKind.SUBJECT,
                primary_key=feed.subject_id,
                source=EvidenceSource.BANK_REGULATOR_HUB,
                region=feed.region,
                confidence=0.9,
            )
            self._graph.link(
                bank_node,
                subject,
                "REPORTS_SUBJECT",
                strength=0.95,
                evidence=[f"bank:{feed.feed_id}"],
            )

        if feed.linked_crypto_address and feed.linked_chain:
            wallet = self._upsert_wallet(feed.linked_crypto_address, feed.linked_chain)
            self._graph.link(
                bank_node,
                wallet,
                "DIRECT_CRYPTO_LINK",
                strength=0.98,
                evidence=["bank_reported_address"],
            )
            if feed.subject_id:
                subject = self._graph.find_node(NodeKind.SUBJECT, feed.subject_id)
                if subject:
                    self._graph.link(
                        subject,
                        wallet,
                        "SUBJECT_OWNS_WALLET",
                        strength=0.85,
                        evidence=["bank_subject_wallet"],
                    )

    def ingest_fiat_event(self, event: FiatLegEvent) -> None:
        fiat_node = self._graph.upsert_node(
            kind=NodeKind.FIAT_EVENT,
            primary_key=event.event_id,
            payload=event.model_dump(),
            source=event.source,
            region=event.region,
            confidence=0.9,
        )
        if event.subject_id:
            subject = self._graph.upsert_node(
                kind=NodeKind.SUBJECT,
                primary_key=event.subject_id,
                region=event.region,
                confidence=0.85,
            )
            self._graph.link(fiat_node, subject, "INVOLVES_SUBJECT", strength=0.9)

        if event.platform_id:
            platform = self._graph.upsert_node(
                kind=NodeKind.PLATFORM,
                primary_key=event.platform_id,
                region=event.region,
                confidence=0.8,
            )
            self._graph.link(fiat_node, platform, "VIA_PLATFORM", strength=0.85)

    def ingest_licensed_event(self, event: LicensedPlatformEvent) -> None:
        platform = self._graph.upsert_node(
            kind=NodeKind.PLATFORM,
            primary_key=event.platform_name,
            region=event.region,
            confidence=0.9,
        )
        wallet = self._upsert_wallet(event.address, event.chain, region=event.region)
        self._graph.link(
            platform,
            wallet,
            "PLATFORM_ADDRESS",
            strength=0.92,
            evidence=[f"{event.direction}:{event.event_id}"],
        )

    def ingest_control_purchase(self, event: ControlPurchaseEvent) -> None:
        cp = self._graph.upsert_node(
            kind=NodeKind.CONTROL_PURCHASE,
            primary_key=event.event_id,
            payload=event.model_dump(),
            source=EvidenceSource.CONTROL_PURCHASE,
            region=event.region,
            confidence=1.0,
        )
        wallet = self._upsert_wallet(event.target_address, event.chain, region=event.region)
        self._graph.link(
            cp,
            wallet,
            "GROUNDED_WALLET",
            strength=1.0,
            evidence=["control_purchase"],
        )
        if event.source_address:
            src = self._upsert_wallet(event.source_address, event.chain, region=event.region)
            self._graph.link(src, wallet, "ON_CHAIN_TRANSFER", strength=0.8)

    def ingest_registry_label(self, label: SovereignRiskLabel) -> None:
        # Sovereign registry hits anchor strongly; sanctioned entries are authoritative.
        weight = 0.95 if label.sanctioned else min(0.9, label.confidence)
        registry_node = self._graph.upsert_node(
            kind=NodeKind.REGISTRY_LABEL,
            primary_key=label.label_id,
            payload=label.model_dump(),
            source=EvidenceSource.SOVEREIGN_REGISTRY,
            confidence=weight,
        )
        wallet = self._upsert_wallet(label.address, label.chain)
        self._graph.link(
            registry_node,
            wallet,
            "LABELS_WALLET",
            strength=weight,
            evidence=[f"registry:{label.source.value}"],
        )

    def ingest_open_osint_mentions(
        self,
        address: str,
        chain: Chain,
        mentions: list[dict[str, object]],
    ) -> None:
        wallet = self._upsert_wallet(address, chain)
        for i, m in enumerate(mentions[:20]):
            key = f"{m.get('source_type')}:{m.get('source_name')}:{i}"
            mention_node = self._graph.upsert_node(
                kind=NodeKind.OSINT_MENTION,
                primary_key=key,
                payload=dict(m),
                source=EvidenceSource.OSINT,
                confidence=float(m.get("confidence") or 0.5),
            )
            self._graph.link(
                mention_node,
                wallet,
                "MENTIONS_WALLET",
                strength=float(m.get("confidence") or 0.5),
                evidence=[f"open_osint:{m.get('source_type')}"],
            )

    def link_bank_to_wallet_by_reference(
        self,
        feed: BankRegulatorFeed,
        wallet_address: str,
        chain: Chain,
        *,
        strength: float,
        evidence: list[str],
    ) -> None:
        bank = self._graph.find_node(NodeKind.BANK_FEED, feed.feed_id)
        if not bank:
            return
        wallet = self._upsert_wallet(wallet_address, chain, region=feed.region)
        self._graph.link(bank, wallet, "INFERRED_BANK_CRYPTO", strength=strength, evidence=evidence)

    def _upsert_wallet(
        self, address: str, chain: Chain, *, region: str | None = None
    ):
        key = _wallet_key(chain, address)
        return self._graph.upsert_node(
            kind=NodeKind.WALLET,
            primary_key=key,
            payload={"address": address, "chain": chain.value},
            source=EvidenceSource.BLOCKCHAIN,
            region=region,
            confidence=0.5,
        )


def _wallet_key(chain: Chain, address: str) -> str:
    normalized = address.lower() if chain == Chain.ETH else address
    return f"{chain.value}:{normalized}"
