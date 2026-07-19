"""Common-input-ownership and shared-funding clustering heuristics."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from flowsint_crypto_compliance.attribution.types import (
    TIER_COSPEND,
    EntityLabel,
)

_EVM_CHAINS = frozenset({"eth", "bsc", "polygon"})
_DEFAULT_BLOCK_WINDOW = 3
_TOKEN_CONTRACTS = frozenset(
    {
        "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",  # USDT TRC20
    }
)


def build_cospend_clusters(
    transfers: list[dict[str, Any]],
    *,
    chain: str,
    focus_address: str | None = None,
    block_window: int | None = None,
    use_evm_v2: bool = False,
) -> list[set[str]]:
    """
    BTC/UTXO: addresses appearing as inputs in the same transaction.
    Account chains (TRON/ETH): addresses sharing the same inbound funder within a tx batch.
    EVM (ETH/BSC/Polygon): recipients of same contract+method within a block window.
    """
    clusters: list[set[str]] = []
    chain_l = chain.lower()
    window = block_window if block_window is not None else (_DEFAULT_BLOCK_WINDOW if not use_evm_v2 else 1)

    if chain_l == "btc":
        by_tx: dict[str, set[str]] = defaultdict(set)
        for tr in transfers:
            txh = str(tr.get("tx_hash") or "")
            frm = tr.get("from") or tr.get("source")
            if txh and frm:
                by_tx[txh].add(str(frm))
        for addrs in by_tx.values():
            if len(addrs) > 1:
                clusters.append(addrs)
        return clusters

    if chain_l in _EVM_CHAINS:
        clusters.extend(
            _evm_contract_method_clusters(
                transfers,
                block_window=window,
                focus_address=focus_address if not use_evm_v2 else None,
            )
        )

    # Account-model: group addresses funded by same source in overlapping time windows
    # Skip known token contracts as funders — otherwise every USDT recipient clusters together.
    by_source: dict[str, set[str]] = defaultdict(set)
    for tr in transfers:
        frm = tr.get("from") or tr.get("source")
        to = tr.get("to") or tr.get("target")
        if not frm or not to or frm == to:
            continue
        if str(frm) in _TOKEN_CONTRACTS or str(to) in _TOKEN_CONTRACTS:
            continue
        by_source[str(frm)].add(str(to))
    for source, targets in by_source.items():
        if len(targets) > 1:
            clusters.append({source, *targets})
        elif focus_address and focus_address in targets:
            clusters.append({source, focus_address})

    return _dedupe_clusters(clusters)


def _evm_contract_method_clusters(
    transfers: list[dict[str, Any]],
    *,
    block_window: int,
    focus_address: str | None,
) -> list[set[str]]:
    """ETH/BSC/Polygon: group recipients funded via same contract+method within block window."""
    buckets: dict[tuple[str, str], list[tuple[int, str]]] = defaultdict(list)
    for tr in transfers:
        contract = tr.get("contract") or tr.get("from")
        method = (tr.get("method_id") or "")[:10]
        to = tr.get("to") or tr.get("target")
        block = int(tr.get("block_number") or 0)
        if not contract or not to or not method or method in ("", "0x"):
            continue
        key = (str(contract).lower(), method)
        buckets[key].append((block, str(to).lower()))

    out: list[set[str]] = []
    for (contract, _method), entries in buckets.items():
        if len(entries) < 2:
            continue
        entries.sort(key=lambda x: x[0])
        window: list[tuple[int, str]] = []
        for block, addr in entries:
            window = [(b, a) for b, a in window if block - b <= block_window]
            window.append((block, addr))
            addrs = {a for _, a in window}
            if len(addrs) > 1:
                cluster = {contract, *addrs}
                if focus_address:
                    focus = focus_address.lower()
                    if focus in cluster:
                        out.append(cluster)
                else:
                    out.append(cluster)
    return out


def _dedupe_clusters(clusters: list[set[str]]) -> list[set[str]]:
    seen: set[frozenset[str]] = set()
    unique: list[set[str]] = []
    for cluster in clusters:
        key = frozenset(cluster)
        if key in seen:
            continue
        seen.add(key)
        unique.append(set(cluster))
    return unique


def propagate_cluster_labels(
    clusters: list[set[str]],
    known: dict[str, EntityLabel],
    *,
    chain: str,
) -> list[EntityLabel]:
    """If one address in a cluster is labeled, propagate Tier-2 label to siblings."""
    out: list[EntityLabel] = []
    for cluster in clusters:
        seeds = [
            known[a]
            for a in cluster
            if a in known
            and known[a].label
            and not _is_token_contract_label(known[a])
        ]
        if not seeds:
            continue
        seed = max(seeds, key=lambda s: (s.tier * -1, s.confidence))
        base_label = _strip_cluster_prefix(seed.label)
        if not base_label or _is_token_contract_name(base_label):
            continue
        cluster_ref = f"cospend:{seed.address[:12]}"
        for addr in cluster:
            if addr in known and known[addr].tier <= TIER_COSPEND:
                continue
            if addr in _TOKEN_CONTRACTS:
                continue
            out.append(
                EntityLabel(
                    address=addr,
                    chain=chain,
                    label=f"cluster:{base_label}",
                    category=seed.category,
                    confidence=min(0.75, seed.confidence * 0.85),
                    source="cospend_cluster",
                    tier=TIER_COSPEND,
                    risk_score=seed.risk_score * 0.9,
                    sanctioned=seed.sanctioned,
                    cluster_ref=cluster_ref,
                    evidence=f"cospend:{seed.address}",
                )
            )
    return out


def _strip_cluster_prefix(label: str) -> str:
    s = (label or "").strip()
    while s.lower().startswith("cluster:"):
        s = s[8:].strip()
    return s


def _is_token_contract_name(name: str) -> bool:
    n = name.lower()
    return "contract" in n or n in {"usdt", "usdc", "trx"}


def _is_token_contract_label(lbl: EntityLabel) -> bool:
    if lbl.address in _TOKEN_CONTRACTS:
        return True
    cat = (lbl.category or "").lower()
    if cat == "payment" and _is_token_contract_name(lbl.label or ""):
        return True
    return _is_token_contract_name(lbl.label or "")
