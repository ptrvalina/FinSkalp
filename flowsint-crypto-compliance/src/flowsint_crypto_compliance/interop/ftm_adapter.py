"""EntityLabel ↔ followthemoney (FTM) entity mapping."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable

from flowsint_crypto_compliance.attribution.entity_label_store import EntityLabelStore
from flowsint_crypto_compliance.attribution.types import TIER_OPEN_DATASET, TIER_SANCTIONS, EntityLabel

_CHAIN_TO_CURRENCY = {
    "tron": "trx",
    "eth": "eth",
    "btc": "btc",
    "bsc": "bnb",
    "polygon": "matic",
}

_CURRENCY_TO_CHAIN = {
    "trx": "tron",
    "tron": "tron",
    "eth": "eth",
    "btc": "btc",
    "bnb": "bsc",
    "matic": "polygon",
}

_SOURCE_DATASETS: dict[str, str] = {
    "ofac_sdn": "ofac",
    "opensanctions": "opensanctions",
    "graphsense": "graphsense",
    "finskalp": "finskalp",
    "sovereign_registry": "finskalp",
    "tronscan": "finskalp",
}


def _stable_ftm_id(chain: str, address: str, source: str = "finskalp") -> str:
    raw = f"{chain}:{address}:{source}"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"ftm-{chain}-{digest}"


def _infer_chain_addr(value: str) -> tuple[str | None, str | None]:
    """Mirror open_datasets chain inference for FTM cryptoWallet values."""
    v = value.strip()
    if v.startswith("0x") and len(v) >= 42:
        return "eth", v.lower()[:42]
    if v.startswith("T") and len(v) == 34:
        return "tron", v
    if re.fullmatch(r"([13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-z0-9]{39,59})", v):
        return "btc", v
    return None, None


def _chain_from_currency(currency: str | None) -> str | None:
    if not currency:
        return None
    return _CURRENCY_TO_CHAIN.get(currency.strip().lower())


def _wallet_only_label(label: EntityLabel) -> bool:
    addr = (label.address or "").strip()
    text = (label.label or "").strip()
    if not text:
        return True
    if text.lower() == addr.lower():
        return True
    if len(text) >= 26 and text in addr:
        return True
    return False


def entity_label_to_ftm_entity(label: EntityLabel) -> dict[str, Any]:
    """Map FinSkalp EntityLabel to an FTM entity JSON object."""
    chain = label.chain.lower()
    currency = _CHAIN_TO_CURRENCY.get(chain, chain)
    schema = "CryptoWallet" if _wallet_only_label(label) else "LegalEntity"
    dataset = _SOURCE_DATASETS.get(label.source, "finskalp")

    topics = [label.category] if label.category else []
    if label.sanctioned:
        topics.append("sanction")

    notes = [
        f"source={label.source}",
        f"category={label.category}",
        f"confidence={label.confidence:.3f}",
        f"tier={label.tier}",
    ]
    if label.evidence:
        notes.append(f"evidence={label.evidence}")
    if label.cluster_ref:
        notes.append(f"cluster_ref={label.cluster_ref}")

    entity: dict[str, Any] = {
        "id": _stable_ftm_id(chain, label.address, label.source),
        "schema": schema,
        "caption": label.label or label.address,
        "datasets": [dataset],
        "properties": {
            "cryptoWallet": [label.address],
            "currency": [currency],
            "topics": topics,
            "notes": notes,
        },
    }
    if schema == "LegalEntity" and label.label:
        entity["properties"]["name"] = [label.label]
    if label.sanctioned:
        entity["properties"]["sanctions"] = [label.source]
    return entity


def ftm_entity_to_entity_label(row: dict[str, Any]) -> EntityLabel | None:
    """Reverse-map FTM entity row to EntityLabel (OpenSanctions-compatible)."""
    props = row.get("properties") or {}
    wallets = props.get("cryptoWallet") or []
    if not wallets:
        return None

    currency = (props.get("currency") or [None])[0]
    chain_hint = _chain_from_currency(str(currency) if currency else "")

    caption = row.get("caption") or ""
    datasets = row.get("datasets") or []
    source = "opensanctions" if "opensanctions" in datasets else "graphsense" if "graphsense" in datasets else "finskalp"
    topics = props.get("topics") or []
    category = str(topics[0]).lower() if topics else "other"
    sanctioned = "sanction" in [str(t).lower() for t in topics] or bool(props.get("sanctions"))
    tier = TIER_SANCTIONS if sanctioned else TIER_OPEN_DATASET

    notes = props.get("notes") or []
    evidence = None
    confidence = 0.85
    for note in notes:
        ns = str(note)
        if ns.startswith("evidence="):
            evidence = ns.split("=", 1)[1]
        if ns.startswith("confidence="):
            try:
                confidence = float(ns.split("=", 1)[1])
            except ValueError:
                pass
        if ns.startswith("source="):
            source = ns.split("=", 1)[1]

    ftm_id = str(row.get("id") or "")[:32]
    if source == "opensanctions" and not evidence:
        evidence = f"opensanctions:{ftm_id}"

    for wallet in wallets:
        chain, addr = _infer_chain_addr(str(wallet))
        if not chain:
            chain = chain_hint
        if not chain or not addr:
            continue
        risk = 90.0 if sanctioned else 20.0
        return EntityLabel(
            address=addr,
            chain=chain,
            label=caption or source,
            category=category,
            confidence=confidence,
            source=source,
            tier=tier,
            risk_score=risk,
            sanctioned=sanctioned,
            evidence=evidence or f"ftm:{ftm_id}",
        )
    return None


def export_labels_ftm_ndjson(labels: Iterable[EntityLabel]) -> str:
    lines = [json.dumps(entity_label_to_ftm_entity(lbl), ensure_ascii=False) for lbl in labels]
    return "\n".join(lines) + ("\n" if lines else "")


def import_labels_from_ftm_ndjson(text: str, store: EntityLabelStore) -> dict[str, Any]:
    loaded = 0
    skipped = 0
    errors: list[str] = []
    for i, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
            lbl = ftm_entity_to_entity_label(row)
            if lbl is None:
                skipped += 1
                continue
            if store.upsert(lbl, force=True):
                loaded += 1
            else:
                skipped += 1
        except json.JSONDecodeError as exc:
            errors.append(f"line {i}: {exc}")
    return {"loaded": loaded, "skipped": skipped, "errors": errors, "total_in_store": store.count()}
