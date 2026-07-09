from __future__ import annotations

from dataclasses import dataclass

from flowsint_types.fiat_crypto import BankRegulatorFeed, Chain, LicensedPlatformEvent

from .evidence_graph import EvidenceEdge, EvidenceGraph, EvidenceNode, NodeKind


@dataclass
class LinkageScore:
    bank_feed_id: str
    wallet_key: str
    score: float
    signals: list[str]


class LinkScorer:
    """
    Score strength of bank ↔ crypto linkage.

    Strong linkage = multiple independent signals aligning.
    """

    def score_path(
        self,
        bank: EvidenceNode,
        edges: list[EvidenceEdge],
        wallet: EvidenceNode,
    ) -> LinkageScore:
        signals: list[str] = []
        score = 0.0

        rel_types = [e.rel_type for e in edges]

        if "DIRECT_CRYPTO_LINK" in rel_types:
            score += 0.45
            signals.append("bank_direct_address")

        if "INFERRED_BANK_CRYPTO" in rel_types:
            inferred = next(e for e in edges if e.rel_type == "INFERRED_BANK_CRYPTO")
            score += inferred.strength * 0.55
            signals.extend(inferred.evidence)

        if "REPORTS_SUBJECT" in rel_types and "SUBJECT_OWNS_WALLET" in rel_types:
            score += 0.25
            signals.append("subject_chain")

        if any(e.rel_type == "VIA_PLATFORM" for e in edges):
            score += 0.2
            signals.append("platform_bridge")

        edge_strength = sum(e.strength for e in edges) / max(len(edges), 1)
        score += edge_strength * 0.15

        bank_payload = bank.payload
        if bank_payload.get("amount") and wallet.payload.get("amount"):
            if _amounts_close(bank_payload["amount"], wallet.payload["amount"]):
                score += 0.15
                signals.append("amount_correlation")

        return LinkageScore(
            bank_feed_id=bank.primary_key,
            wallet_key=wallet.primary_key,
            score=round(min(1.0, score), 3),
            signals=signals,
        )

    def score_bank_platform_wallet(
        self,
        feed: BankRegulatorFeed,
        platform_event: LicensedPlatformEvent,
        *,
        amount_tolerance: float = 0.15,
    ) -> LinkageScore:
        signals: list[str] = []
        score = 0.35

        if feed.region and platform_event.region:
            if feed.region.upper() == platform_event.region.upper():
                score += 0.15
                signals.append("region_match")

        if feed.amount and platform_event.amount_fiat:
            if _amounts_close(feed.amount, platform_event.amount_fiat, amount_tolerance):
                score += 0.25
                signals.append("fiat_amount_match")

        if feed.linked_crypto_address == platform_event.address:
            score += 0.35
            signals.append("address_exact_match")

        wallet_key = f"{platform_event.chain.value}:{platform_event.address}"
        return LinkageScore(
            bank_feed_id=feed.feed_id,
            wallet_key=wallet_key,
            score=round(min(1.0, score), 3),
            signals=signals,
        )


def _amounts_close(a: float, b: float, tolerance: float = 0.1) -> bool:
    if a <= 0 or b <= 0:
        return False
    return abs(a - b) / max(a, b) <= tolerance
