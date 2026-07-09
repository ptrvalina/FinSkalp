"""Scalpel → EvidenceGraph bridge (avoids circular imports)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flowsint_crypto_compliance.osint_core.evidence_graph import EvidenceGraph, NodeKind
from flowsint_types.fiat_crypto import Chain, EvidenceSource

if TYPE_CHECKING:
    from flowsint_crypto_compliance.osint_core.scalpel.engine import ScalpelResult


def scalpel_case_ref(address: str, chain: Chain) -> str:
    safe = address.replace(":", "_")[:48]
    return f"SCALPEL-{chain.value.upper()}-{safe}"


def build_scalpel_evidence_graph(result: ScalpelResult) -> EvidenceGraph:
    graph = EvidenceGraph()
    wallet_key = f"{result.chain.value}:{result.address}"
    wallet = graph.upsert_node(
        kind=NodeKind.WALLET,
        primary_key=wallet_key,
        payload={"address": result.address, "chain": result.chain.value},
        source=EvidenceSource.OSINT,
        confidence=0.7,
    )

    for i, mention in enumerate(result.mentions):
        m_node = graph.upsert_node(
            kind=NodeKind.OSINT_MENTION,
            primary_key=f"{wallet_key}:m{i}",
            payload=mention.to_dict(),
            source=EvidenceSource.OSINT,
            confidence=mention.confidence,
        )
        graph.link(
            wallet,
            m_node,
            "OSINT_MENTION",
            strength=mention.confidence,
            evidence=[mention.source_type],
        )

    agg = result.extracted_entities.get("aggregate") or {}
    for inn in agg.get("inn") or []:
        inn_node = graph.upsert_node(
            kind=NodeKind.SUBJECT,
            primary_key=f"inn:{inn}",
            payload={"inn": inn, "entity_type": "inn"},
            source=EvidenceSource.OSINT,
            confidence=0.75,
        )
        graph.link(wallet, inn_node, "LINKED_INN", strength=0.72, evidence=["scalpel_extract"])

    for phone in agg.get("phones") or []:
        ph_node = graph.upsert_node(
            kind=NodeKind.SUBJECT,
            primary_key=f"phone:{phone}",
            payload={"phone": phone, "entity_type": "phone"},
            source=EvidenceSource.OSINT,
            confidence=0.7,
        )
        graph.link(wallet, ph_node, "LINKED_PHONE", strength=0.68, evidence=["scalpel_extract"])

    for username in agg.get("usernames") or []:
        u_node = graph.upsert_node(
            kind=NodeKind.SUBJECT,
            primary_key=f"user:{username}",
            payload={"username": username, "entity_type": "username"},
            source=EvidenceSource.OSINT,
            confidence=0.65,
        )
        graph.link(wallet, u_node, "LINKED_USERNAME", strength=0.65, evidence=["scalpel_extract"])

    for label in result.proposed_labels:
        src = getattr(label.source, "value", str(label.source))
        if src in ("internal_osint", "cbr", "other"):
            vasp = graph.upsert_node(
                kind=NodeKind.PLATFORM,
                primary_key=label.label_id or label.address,
                payload=label.model_dump(),
                source=EvidenceSource.SOVEREIGN_REGISTRY,
                confidence=label.confidence,
            )
            graph.link(wallet, vasp, "LINKED_VASP", strength=label.confidence, evidence=["vasp_registry"])

    return graph
