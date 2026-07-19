"""Scalpel → EvidenceGraph bridge (avoids circular imports)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from flowsint_crypto_compliance.osint_core.evidence_graph import EvidenceGraph, NodeKind
from flowsint_types.fiat_crypto import Chain, EvidenceSource

if TYPE_CHECKING:
    from flowsint_crypto_compliance.osint_core.scalpel.engine import ScalpelResult

_SANCTION_TAGS = frozenset(
    {"sanctions_screening", "sanctions", "ofac", "sdn", "terrorism", "proliferation"}
)
_SCAM_TAGS = frozenset(
    {
        "scam_report",
        "scam",
        "abuse",
        "ransomware",
        "phishing",
        "fraud",
        "darknet",
        "mixer",
        "mixer_like",
        "stolen",
    }
)
_VASP_TAGS = frozenset({"licensed_vasp", "otc_exchange", "exchange", "vasp"})
_OWNER_CATS = frozenset(
    {"exchange", "vasp", "payment", "gambling", "mixer", "individual", "person", "organization", "otc"}
)


def scalpel_case_ref(address: str, chain: Chain) -> str:
    safe = address.replace(":", "_")[:48]
    return f"SCALPEL-{chain.value.upper()}-{safe}"


def serialize_evidence_graph(graph: EvidenceGraph) -> dict[str, Any]:
    """API-safe graph payload for merge + UI visualization (keeps risk/attribution)."""
    nodes: list[dict[str, Any]] = []
    for node in graph.nodes:
        payload = dict(node.payload or {})
        display = (
            payload.get("display_label")
            or payload.get("attribution")
            or payload.get("owner")
            or node.primary_key
        )
        row: dict[str, Any] = {
            "id": node.node_id,
            "kind": node.kind.value,
            "label": display,
            "region": node.region,
            "confidence": node.confidence,
            "primary_key": node.primary_key,
        }
        for key in (
            "address",
            "chain",
            "role",
            "attribution",
            "owner",
            "owner_category",
            "sanctioned",
            "scam",
            "flags",
            "risk_tags",
            "source_label",
            "display_label",
        ):
            if key in payload and payload[key] is not None:
                row[key] = payload[key]
        nodes.append(row)

    edges: list[dict[str, Any]] = []
    for edge in graph.edges:
        edges.append(
            {
                "id": edge.edge_id,
                "source": edge.from_id,
                "target": edge.to_id,
                "rel_type": edge.rel_type,
                "strength": edge.strength,
                "evidence": list(edge.evidence or []),
            }
        )
    return {"nodes": nodes, "edges": edges}


def build_scalpel_evidence_graph(result: ScalpelResult) -> EvidenceGraph:
    graph = EvidenceGraph()
    wallet_key = f"{result.chain.value}:{result.address}"
    wallet = graph.upsert_node(
        kind=NodeKind.WALLET,
        primary_key=wallet_key,
        payload={"address": result.address, "chain": result.chain.value, "role": "seed"},
        source=EvidenceSource.OSINT,
        confidence=0.7,
    )

    # Mentions: attach to the wallet they screen (seed or hop-1 counterparty)
    for i, mention in enumerate(result.mentions):
        mention_addr = (mention.address or result.address or "").strip()
        m_node = graph.upsert_node(
            kind=NodeKind.OSINT_MENTION,
            primary_key=f"{wallet_key}:m{i}",
            payload=mention.to_dict(),
            source=EvidenceSource.OSINT,
            confidence=mention.confidence,
        )
        anchor = _wallet_node_for_address(graph, result, mention_addr) or wallet
        graph.link(
            anchor,
            m_node,
            "OSINT_MENTION",
            strength=mention.confidence,
            evidence=[mention.source_type, mention.risk_tag or ""],
        )

    _project_onchain_counterparties(graph, wallet, result)
    _project_extracted_subjects(graph, wallet, result)
    _project_proposed_vasp_labels(graph, wallet, result)
    _annotate_risk_and_attribution(graph, result)
    _upgrade_flagged_transfer_edges(graph)

    return graph


def _wallet_node_for_address(
    graph: EvidenceGraph,
    result: ScalpelResult,
    address: str,
) -> Any | None:
    if not address:
        return None
    chain = result.chain.value
    key = f"{chain}:{address}"
    for node in graph.nodes:
        if node.kind == NodeKind.WALLET and (
            node.primary_key == key
            or (node.payload or {}).get("address", "").lower() == address.lower()
        ):
            return node
    # Create wallet for hop-1 screened CP that wasn't transferred yet
    if address.lower() != result.address.lower() and address != result.address:
        return graph.upsert_node(
            kind=NodeKind.WALLET,
            primary_key=key,
            payload={"address": address, "chain": chain, "role": "counterparty"},
            source=EvidenceSource.OSINT,
            confidence=0.7,
        )
    return None


def _collect_onchain_entities(result: ScalpelResult) -> tuple[list[str], list[dict[str, Any]]]:
    """Pull counterparties + transfers from onchain_explorer collector entities."""
    by_collector = (result.extracted_entities or {}).get("by_collector") or {}
    counterparties: list[str] = []
    transfers: list[dict[str, Any]] = []
    for key, payload in by_collector.items():
        if not isinstance(payload, dict):
            continue
        if "onchain" not in str(key).lower() and "blockchain" not in str(key).lower():
            if "counterparties" not in payload and "transfers" not in payload:
                continue
        for cp in payload.get("counterparties") or []:
            addr = str(cp).strip()
            if addr and addr not in counterparties:
                counterparties.append(addr)
        for tr in payload.get("transfers") or []:
            if isinstance(tr, dict):
                transfers.append(tr)
    for item in ((result.extracted_entities or {}).get("aggregate") or {}).get("crypto_addresses") or []:
        addr = (item.get("address") if isinstance(item, dict) else None) or ""
        addr = str(addr).strip()
        if addr and addr != result.address and addr not in counterparties:
            counterparties.append(addr)
    return counterparties[:40], transfers[:80]


def _project_onchain_counterparties(
    graph: EvidenceGraph,
    seed_wallet: Any,
    result: ScalpelResult,
) -> None:
    counterparties, transfers = _collect_onchain_entities(result)
    chain = result.chain.value
    seed_addr = result.address

    linked: set[str] = set()
    for tr in transfers:
        frm = str(tr.get("from") or "").strip()
        to = str(tr.get("to") or "").strip()
        if not frm or not to:
            continue
        asset = str(tr.get("asset") or "CRYPTO")
        direction = "out" if frm.lower() == seed_addr.lower() or frm == seed_addr else "in"
        other = to if direction == "out" else frm
        if not other or other.lower() == seed_addr.lower() or other == seed_addr:
            continue
        cp_key = f"{chain}:{other}"
        cp_node = graph.upsert_node(
            kind=NodeKind.WALLET,
            primary_key=cp_key,
            payload={
                "address": other,
                "chain": chain,
                "role": "counterparty",
                "asset": asset,
                "tx_hash": tr.get("tx_hash"),
                "amount": tr.get("amount"),
            },
            source=EvidenceSource.BLOCKCHAIN,
            confidence=0.82,
        )
        rel = "TRANSFER_OUT" if direction == "out" else "TRANSFER_IN"
        graph.link(
            seed_wallet,
            cp_node,
            rel,
            strength=0.8,
            evidence=["onchain_explorer", asset],
        )
        linked.add(other.lower())

    for cp in counterparties:
        if cp.lower() in linked or cp.lower() == seed_addr.lower() or cp == seed_addr:
            continue
        cp_key = f"{chain}:{cp}"
        cp_node = graph.upsert_node(
            kind=NodeKind.WALLET,
            primary_key=cp_key,
            payload={"address": cp, "chain": chain, "role": "counterparty"},
            source=EvidenceSource.BLOCKCHAIN,
            confidence=0.75,
        )
        graph.link(
            seed_wallet,
            cp_node,
            "COUNTERPARTY",
            strength=0.72,
            evidence=["onchain_explorer"],
        )


def _project_extracted_subjects(
    graph: EvidenceGraph,
    wallet: Any,
    result: ScalpelResult,
) -> None:
    agg = result.extracted_entities.get("aggregate") or {}
    for inn in agg.get("inn") or []:
        inn_node = graph.upsert_node(
            kind=NodeKind.SUBJECT,
            primary_key=f"inn:{inn}",
            payload={"inn": inn, "entity_type": "inn", "owner_category": "organization"},
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
            payload={
                "username": username,
                "entity_type": "username",
                "owner_category": "individual",
                "display_label": f"@{username}",
            },
            source=EvidenceSource.OSINT,
            confidence=0.65,
        )
        graph.link(wallet, u_node, "LINKED_USERNAME", strength=0.65, evidence=["scalpel_extract"])


def _project_proposed_vasp_labels(
    graph: EvidenceGraph,
    wallet: Any,
    result: ScalpelResult,
) -> None:
    for label in result.proposed_labels:
        src = getattr(label.source, "value", str(label.source))
        if src not in ("internal_osint", "cbr", "other"):
            continue
        name = getattr(label, "label", None) or label.label_id or label.address
        vasp = graph.upsert_node(
            kind=NodeKind.PLATFORM,
            primary_key=label.label_id or str(name),
            payload={
                **(label.model_dump() if hasattr(label, "model_dump") else {}),
                "display_label": str(name),
                "owner_category": "vasp",
                "attribution": str(name),
            },
            source=EvidenceSource.SOVEREIGN_REGISTRY,
            confidence=label.confidence,
        )
        graph.link(wallet, vasp, "LINKED_VASP", strength=label.confidence, evidence=["vasp_registry"])


def _lookup_tronscan_tag_sync(address: str):
    """Best-effort sync TronScan public tag → EntityLabel (exchange / person / org)."""
    import httpx
    from flowsint_crypto_compliance.attribution.types import TIER_OPEN_DATASET, EntityLabel
    from flowsint_crypto_compliance.attribution.open_datasets import _category_risk, _infer_category

    with httpx.Client(timeout=6.0) as client:
        resp = client.get(
            "https://apilist.tronscanapi.com/api/accountv2",
            params={"address": address},
        )
    if resp.status_code != 200:
        return None
    data = resp.json() or {}
    tag = data.get("tag") or data.get("name") or data.get("publicTag")
    if not tag:
        return None
    cat = _infer_category(str(tag))
    # Heuristic: human-looking names → individual
    if cat == "other" and " " in str(tag) and not any(ch.isdigit() for ch in str(tag)[:3]):
        cat = "individual"
    return EntityLabel(
        address=address,
        chain="tron",
        label=str(tag),
        category=cat,
        confidence=0.72,
        source="tronscan",
        tier=TIER_OPEN_DATASET,
        risk_score=_category_risk(cat),
        evidence="tronscan:accountv2",
    )


def _clean_attr_label(raw: str | None) -> str:
    s = (raw or "").strip()
    while s.lower().startswith("cluster:"):
        s = s[8:].strip()
    return s


def _is_usable_attribution(lbl: Any, address: str) -> bool:
    """Drop poisoned cospend/kyt contract tags that are not real ownership."""
    name = _clean_attr_label(getattr(lbl, "label", None))
    if not name:
        return False
    cat = (getattr(lbl, "category", None) or "").lower()
    source = (getattr(lbl, "source", None) or "").lower()
    if "contract" in name.lower() and cat in {"payment", "other", ""}:
        # Only attribute the token contract address itself
        return address == getattr(lbl, "address", None)
    if source in {"kyt_import", "cospend_cluster"} and cat in {"other", "payment"}:
        if getattr(lbl, "confidence", 0) < 0.7:
            return False
    if cat in {"sanctions", "scam", "abuse", "ransomware", "darknet", "mixer", "stolen"}:
        return True
    if cat in _OWNER_CATS:
        return True
    if bool(getattr(lbl, "sanctioned", False)):
        return True
    return float(getattr(lbl, "confidence", 0) or 0) >= 0.75


def _annotate_risk_and_attribution(graph: EvidenceGraph, result: ScalpelResult) -> None:
    """Apply live scalpel hits + local OFAC/exchange seeds onto wallet nodes."""
    flags_by_addr: dict[str, dict[str, Any]] = {}

    for mention in result.mentions:
        addr = (mention.address or "").strip()
        if not addr:
            continue
        tag = (mention.risk_tag or "").lower()
        slot = flags_by_addr.setdefault(
            addr.lower(),
            {
                "address": addr,
                "sanctioned": False,
                "scam": False,
                "risk_tags": [],
                "titles": [],
                "attribution": None,
                "owner_category": None,
                "source_label": None,
                "confidence": 0.0,
            },
        )
        if tag and tag not in slot["risk_tags"]:
            slot["risk_tags"].append(tag)
        if mention.title_ru:
            slot["titles"].append(mention.title_ru)
        slot["confidence"] = max(float(slot["confidence"]), float(mention.confidence or 0))

        if tag in _SANCTION_TAGS or "sanction" in tag:
            slot["sanctioned"] = True
            slot["attribution"] = slot["attribution"] or mention.title_ru or "Sanctions hit"
            slot["owner_category"] = "sanctions"
            slot["source_label"] = mention.source_name
            _link_registry_flag(
                graph,
                result,
                addr,
                flag="sanctioned",
                label=mention.title_ru or "Sanctions",
                rel="SANCTIONED_HIT",
                confidence=mention.confidence,
                evidence=[mention.source_name or "sanctions", tag],
            )
        if tag in _SCAM_TAGS or "scam" in tag or "abuse" in tag:
            slot["scam"] = True
            slot["attribution"] = slot["attribution"] or mention.title_ru or "Scam/Abuse"
            slot["owner_category"] = slot["owner_category"] or "scam"
            slot["source_label"] = slot["source_label"] or mention.source_name
            _link_registry_flag(
                graph,
                result,
                addr,
                flag="scam",
                label=mention.title_ru or "Scam / Abuse",
                rel="SCAM_HIT",
                confidence=mention.confidence,
                evidence=[mention.source_name or "abuse", tag],
            )
        if tag in _VASP_TAGS:
            slot["attribution"] = slot["attribution"] or mention.title_ru or mention.source_name
            slot["owner_category"] = "vasp"

    # Local attribution datasets (exchange seeds, cached OFAC/OpenSanctions)
    try:
        from flowsint_crypto_compliance.attribution.entity_label_store import get_entity_label_store
        from flowsint_crypto_compliance.attribution.open_datasets import ensure_local_attribution_seeds

        store = get_entity_label_store()
        ensure_local_attribution_seeds(store)
        chain = result.chain.value
        wallets = [
            n
            for n in graph.nodes
            if n.kind == NodeKind.WALLET and (n.payload or {}).get("address")
        ]
        tronscan_budget = 8
        for node in wallets:
            addr = str((node.payload or {}).get("address"))
            lbl = store.lookup(chain, addr)
            if not lbl:
                lbl = store.lookup(chain, addr.lower()) if chain != "tron" else None
            if not lbl or not _is_usable_attribution(lbl, addr):
                # Live TronScan public tag (exchange / person) for unlabeled CPs
                if tronscan_budget > 0 and not (node.payload or {}).get("attribution"):
                    tronscan_budget -= 1
                    try:
                        lbl = _lookup_tronscan_tag_sync(addr)
                    except Exception:
                        lbl = None
                else:
                    lbl = None
            if not lbl or not _is_usable_attribution(lbl, addr):
                continue
            clean_name = _clean_attr_label(lbl.label)
            slot = flags_by_addr.setdefault(
                addr.lower(),
                {
                    "address": addr,
                    "sanctioned": False,
                    "scam": False,
                    "risk_tags": [],
                    "titles": [],
                    "attribution": None,
                    "owner_category": None,
                    "source_label": None,
                    "confidence": 0.0,
                },
            )
            if lbl.sanctioned or (lbl.category or "").lower() == "sanctions":
                slot["sanctioned"] = True
                if "sanctions" not in slot["risk_tags"]:
                    slot["risk_tags"].append("sanctions")
            cat = (lbl.category or "").lower()
            if cat in {"scam", "abuse", "ransomware", "darknet", "mixer", "stolen"}:
                slot["scam"] = True
                if cat not in slot["risk_tags"]:
                    slot["risk_tags"].append(cat)
            if clean_name:
                slot["attribution"] = clean_name
                slot["owner_category"] = cat or slot["owner_category"]
                slot["source_label"] = lbl.source
                slot["confidence"] = max(float(slot["confidence"]), float(lbl.confidence or 0))
            # Pass cleaned label name into graph helpers
            if clean_name and clean_name != lbl.label:
                from dataclasses import replace

                lbl = replace(lbl, label=clean_name)
            _apply_entity_label_to_graph(graph, result, node, lbl)
    except Exception:
        pass

    for addr_l, slot in flags_by_addr.items():
        for node in graph.nodes:
            if node.kind != NodeKind.WALLET:
                continue
            na = str((node.payload or {}).get("address") or "")
            if na.lower() != addr_l:
                continue
            flags = list((node.payload or {}).get("flags") or [])
            if slot["sanctioned"] and "sanctioned" not in flags:
                flags.append("sanctioned")
            if slot["scam"] and "scam" not in flags:
                flags.append("scam")
            display_bits = []
            if slot["sanctioned"]:
                display_bits.append("SANCTIONS")
            if slot["scam"]:
                display_bits.append("SCAM")
            if slot.get("attribution"):
                display_bits.append(str(slot["attribution"])[:40])
            display_bits.append(na if len(na) <= 22 else f"{na[:10]}…{na[-6:]}")
            graph.upsert_node(
                kind=NodeKind.WALLET,
                primary_key=node.primary_key,
                payload={
                    **(node.payload or {}),
                    "sanctioned": bool(slot["sanctioned"] or (node.payload or {}).get("sanctioned")),
                    "scam": bool(slot["scam"] or (node.payload or {}).get("scam")),
                    "flags": flags,
                    "risk_tags": list(
                        dict.fromkeys(
                            list((node.payload or {}).get("risk_tags") or []) + list(slot["risk_tags"])
                        )
                    ),
                    "attribution": slot.get("attribution") or (node.payload or {}).get("attribution"),
                    "owner": slot.get("attribution") or (node.payload or {}).get("owner"),
                    "owner_category": slot.get("owner_category")
                    or (node.payload or {}).get("owner_category"),
                    "source_label": slot.get("source_label") or (node.payload or {}).get("source_label"),
                    "display_label": " · ".join(display_bits),
                },
                confidence=max(node.confidence, float(slot.get("confidence") or 0) or node.confidence),
            )


def _link_registry_flag(
    graph: EvidenceGraph,
    result: ScalpelResult,
    address: str,
    *,
    flag: str,
    label: str,
    rel: str,
    confidence: float,
    evidence: list[str],
) -> None:
    wallet = _wallet_node_for_address(graph, result, address)
    if wallet is None:
        chain = result.chain.value
        wallet = graph.upsert_node(
            kind=NodeKind.WALLET,
            primary_key=f"{chain}:{address}",
            payload={"address": address, "chain": chain, "role": "counterparty"},
            source=EvidenceSource.OSINT,
            confidence=confidence,
        )
    reg = graph.upsert_node(
        kind=NodeKind.REGISTRY_LABEL,
        primary_key=f"{flag}:{address[:24]}:{label[:32]}",
        payload={
            "flag": flag,
            "display_label": label,
            "attribution": label,
            "address": address,
            "owner_category": flag,
        },
        source=EvidenceSource.SOVEREIGN_REGISTRY,
        confidence=confidence,
    )
    graph.link(wallet, reg, rel, strength=max(0.75, confidence), evidence=evidence)


def _apply_entity_label_to_graph(
    graph: EvidenceGraph,
    result: ScalpelResult,
    wallet: Any,
    lbl: Any,
) -> None:
    name = _clean_attr_label(lbl.label) or lbl.category or "Attributed"
    cat = (lbl.category or "unknown").lower()
    if lbl.sanctioned or cat == "sanctions":
        _link_registry_flag(
            graph,
            result,
            str((wallet.payload or {}).get("address") or result.address),
            flag="sanctioned",
            label=name,
            rel="SANCTIONED_HIT",
            confidence=float(lbl.confidence or 0.9),
            evidence=[lbl.source or "ofac", "local_dataset"],
        )
        return
    if cat in {"scam", "abuse", "ransomware", "darknet", "mixer", "stolen"}:
        _link_registry_flag(
            graph,
            result,
            str((wallet.payload or {}).get("address") or result.address),
            flag="scam",
            label=name,
            rel="SCAM_HIT",
            confidence=float(lbl.confidence or 0.8),
            evidence=[lbl.source or "abuse", "local_dataset"],
        )
        return
    if cat not in _OWNER_CATS and not (float(lbl.confidence or 0) >= 0.8 and cat not in {"other", "payment"}):
        return
    if "contract" in name.lower() and cat in {"payment", "other"}:
        # Contract tags only on the contract address itself
        if str((wallet.payload or {}).get("address")) != lbl.address:
            return
    owner_node = graph.upsert_node(
        kind=NodeKind.PLATFORM if cat in {"exchange", "vasp", "payment", "gambling"} else NodeKind.SUBJECT,
        primary_key=f"owner:{cat}:{name}"[:96],
        payload={
            "display_label": name,
            "attribution": name,
            "owner_category": cat,
            "source_label": lbl.source,
        },
        source=EvidenceSource.SOVEREIGN_REGISTRY,
        confidence=float(lbl.confidence or 0.75),
    )
    graph.link(
        wallet,
        owner_node,
        "ATTRIBUTED_TO",
        strength=float(lbl.confidence or 0.75),
        evidence=[lbl.source or "attribution", cat],
    )


def _upgrade_flagged_transfer_edges(graph: EvidenceGraph) -> None:
    """If seed transferred to a sanctioned/scam wallet, expose explicit edge types."""
    by_id = {n.node_id: n for n in graph.nodes}
    for edge in list(graph.edges):
        if edge.rel_type not in {"TRANSFER_OUT", "TRANSFER_IN", "COUNTERPARTY"}:
            continue
        target = by_id.get(edge.to_id)
        source = by_id.get(edge.from_id)
        other = target
        if not other or other.kind != NodeKind.WALLET:
            other = source if source and source.kind == NodeKind.WALLET else None
        if not other:
            continue
        payload = other.payload or {}
        if payload.get("sanctioned"):
            new_rel = (
                "TRANSFER_OUT_SANCTIONED"
                if edge.rel_type == "TRANSFER_OUT"
                else "TRANSFER_IN_SANCTIONED"
                if edge.rel_type == "TRANSFER_IN"
                else "COUNTERPARTY_SANCTIONED"
            )
            edge.rel_type = new_rel
            edge.strength = max(edge.strength, 0.95)
            if "sanctions" not in edge.evidence:
                edge.evidence = list(edge.evidence) + ["sanctions"]
        elif payload.get("scam"):
            new_rel = (
                "TRANSFER_OUT_SCAM"
                if edge.rel_type == "TRANSFER_OUT"
                else "TRANSFER_IN_SCAM"
                if edge.rel_type == "TRANSFER_IN"
                else "COUNTERPARTY_SCAM"
            )
            edge.rel_type = new_rel
            edge.strength = max(edge.strength, 0.9)
            if "scam" not in edge.evidence:
                edge.evidence = list(edge.evidence) + ["scam"]
