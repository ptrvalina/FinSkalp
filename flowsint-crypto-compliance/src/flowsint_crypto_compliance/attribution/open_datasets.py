"""Bootstrap open label datasets: OFAC, OpenSanctions, GraphSense, TronScan."""

from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import httpx

from flowsint_crypto_compliance.attribution.entity_label_store import EntityLabelStore
from flowsint_crypto_compliance.attribution.types import (
    TIER_OPEN_DATASET,
    TIER_SANCTIONS,
    EntityLabel,
)

_log = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "attribution"
_OFAC_URL = os.getenv(
    "FINSKALP_OFAC_URL",
    "https://www.treasury.gov/ofac/downloads/sanctions/1.0/sdn_advanced.xml",
)
_OPENSANCTIONS_CRYPTO_URL = os.getenv(
    "FINSKALP_OPENSANCTIONS_CRYPTO_URL",
    "https://data.opensanctions.org/datasets/latest/sanctions/entities.ftm.json",
)
_TRONSCAN_ACCOUNT = "https://apilist.tronscanapi.com/api/accountv2"
_BOOTSTRAPPED = False


async def bootstrap_open_datasets(store: EntityLabelStore) -> dict[str, Any]:
    """Load all open datasets once at startup; degrade gracefully per source."""
    global _BOOTSTRAPPED

    from flowsint_crypto_compliance.attribution.postgres_entity_store import (
        record_bootstrap,
        should_skip_bootstrap,
    )

    if _BOOTSTRAPPED:
        return {"status": "ok", "total": store.count(), "sources": {}}

    if should_skip_bootstrap():
        _BOOTSTRAPPED = True
        return {"status": "cached", "total": store.count(), "sources": {}}

    stats: dict[str, Any] = {"sources": {}, "errors": [], "total": 0}

    # Fast local seeds first — attribution works immediately without network
    for name, loader in [
        ("tronscan_seed", _load_tronscan_seed),
        ("graphsense", _load_graphsense_bundled),
        ("graphsense_tagpack", _load_graphsense_tagpack),
    ]:
        try:
            labels = await loader()
            n = store.bulk_upsert(labels)
            stats["sources"][name] = {"loaded": len(labels), "upserted": n}
        except Exception as exc:
            stats["errors"].append({name: str(exc)})

    network_loaders = [("ofac_sdn", _load_ofac), ("opensanctions", _load_opensanctions_crypto)]
    for name, loader in network_loaders:
        try:
            labels = await asyncio.wait_for(loader(), timeout=20.0)
            n = store.bulk_upsert(labels)
            stats["sources"][name] = {"loaded": len(labels), "upserted": n}
        except Exception as exc:
            stats["errors"].append({name: str(exc)})
            stats["sources"][name] = {"loaded": 0, "error": str(exc)}
            _log.warning("Attribution bootstrap %s failed: %s", name, exc)

    stats["total"] = store.count()
    _BOOTSTRAPPED = True
    record_bootstrap(stats)
    return stats


async def lookup_tronscan_tag(address: str) -> EntityLabel | None:
    """Live TronScan public account tag lookup."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(_TRONSCAN_ACCOUNT, params={"address": address})
        if resp.status_code != 200:
            return None
        data = resp.json() or {}
        tag = data.get("tag") or data.get("name") or data.get("publicTag")
        if not tag:
            return None
        category = _infer_category(str(tag))
        return EntityLabel(
            address=address,
            chain="tron",
            label=str(tag),
            category=category,
            confidence=0.7,
            source="tronscan",
            tier=TIER_OPEN_DATASET,
            risk_score=_category_risk(category),
            evidence="tronscan:accountv2",
        )
    except Exception:
        return None


async def _load_ofac() -> list[EntityLabel]:
    cached = _DATA_DIR / "ofac_crypto.json"
    if cached.is_file() and os.getenv("FINSKALP_OFAC_REFRESH", "0") != "1":
        return _labels_from_json(cached, source="ofac_sdn", tier=TIER_SANCTIONS, sanctioned=True)

    labels: list[EntityLabel] = []
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.get(_OFAC_URL)
        if resp.status_code == 200:
            labels = _parse_ofac_xml(resp.text)
            if labels:
                cached.parent.mkdir(parents=True, exist_ok=True)
                cached.write_text(
                    json.dumps([l.to_dict() for l in labels], ensure_ascii=False),
                    encoding="utf-8",
                )
    except Exception:
        pass

    if not labels and cached.is_file():
        return _labels_from_json(cached, source="ofac_sdn", tier=TIER_SANCTIONS, sanctioned=True)
    return labels


def _parse_ofac_xml(xml_text: str) -> list[EntityLabel]:
    labels: list[EntityLabel] = []
    root = ET.fromstring(xml_text)
    ns = {"sdn": "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/XML"}
    for feature in root.iter():
        if not feature.tag.endswith("Feature"):
            continue
        ftype = ""
        value = ""
        for child in feature:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag == "FeatureType":
                ftype = (child.text or "").lower()
            if tag in ("FeatureVersion", "VersionDetail"):
                for sub in child.iter():
                    st = sub.tag.split("}")[-1] if "}" in sub.tag else sub.tag
                    if st in ("VersionDetail", "Value") and sub.text:
                        value = sub.text.strip()
        if not value:
            continue
        chain, addr = _parse_crypto_value(value, ftype)
        if not chain or not addr:
            continue
        labels.append(
            EntityLabel(
                address=addr,
                chain=chain,
                label="OFAC SDN",
                category="sanctions",
                confidence=0.99,
                source="ofac_sdn",
                tier=TIER_SANCTIONS,
                risk_score=95.0,
                sanctioned=True,
                evidence="ofac:sdn_advanced",
            )
        )
    return labels


def _parse_crypto_value(value: str, ftype: str) -> tuple[str | None, str | None]:
    v = value.strip()
    if v.startswith("0x") and len(v) == 42:
        return "eth", v.lower()
    if v.startswith("T") and len(v) == 34:
        return "tron", v
    if re.fullmatch(r"([13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-z0-9]{39,59})", v):
        return "btc", v
    if "tron" in ftype and v.startswith("T"):
        return "tron", v
    if "bitcoin" in ftype or "xbt" in ftype:
        return "btc", v
    if "ethereum" in ftype or "eth" in ftype:
        return "eth", v.lower() if v.startswith("0x") else None
    return None, None


async def _load_opensanctions_crypto() -> list[EntityLabel]:
    cached = _DATA_DIR / "opensanctions_crypto.json"
    if cached.is_file() and os.getenv("FINSKALP_OS_REFRESH", "0") != "1":
        return _labels_from_json(cached, source="opensanctions", tier=TIER_SANCTIONS, sanctioned=True)

    labels: list[EntityLabel] = []
    try:
        async with httpx.AsyncClient(timeout=90.0, follow_redirects=True) as client:
            resp = await client.get(_OPENSANCTIONS_CRYPTO_URL)
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}")
        for line in resp.text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            for prop in row.get("properties", {}).get("cryptoWallet", []) or []:
                chain, addr = _infer_chain_addr(str(prop))
                if chain and addr:
                    labels.append(
                        EntityLabel(
                            address=addr,
                            chain=chain,
                            label=row.get("caption") or "OpenSanctions",
                            category="sanctions",
                            confidence=0.92,
                            source="opensanctions",
                            tier=TIER_SANCTIONS,
                            risk_score=90.0,
                            sanctioned=True,
                            evidence=f"opensanctions:{row.get('id', '')[:16]}",
                        )
                    )
        if labels:
            cached.parent.mkdir(parents=True, exist_ok=True)
            cached.write_text(
                json.dumps([l.to_dict() for l in labels[:50000]], ensure_ascii=False),
                encoding="utf-8",
            )
    except Exception:
        if cached.is_file():
            return _labels_from_json(cached, source="opensanctions", tier=TIER_SANCTIONS, sanctioned=True)
        raise
    return labels


async def _load_graphsense_bundled() -> list[EntityLabel]:
    path = _DATA_DIR / "graphsense_seed.csv"
    if not path.is_file():
        return []
    labels: list[EntityLabel] = []
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            chain = (row.get("chain") or "").lower()
            addr = row.get("address") or ""
            if not chain or not addr:
                continue
            labels.append(
                EntityLabel(
                    address=addr,
                    chain=chain,
                    label=row.get("label") or row.get("entity") or "GraphSense",
                    category=(row.get("category") or "exchange").lower(),
                    confidence=float(row.get("confidence") or 0.8),
                    source="graphsense",
                    tier=TIER_OPEN_DATASET,
                    risk_score=float(row.get("risk_score") or 15),
                    evidence="graphsense:seed",
                )
            )
    return labels


async def _load_graphsense_tagpack() -> list[EntityLabel]:
    from flowsint_crypto_compliance.interop.graphsense_tagpack import bootstrap_tagpack

    return await bootstrap_tagpack()


async def _load_tronscan_seed() -> list[EntityLabel]:
    path = _DATA_DIR / "tron_exchange_seed.json"
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    labels: list[EntityLabel] = []
    for row in raw if isinstance(raw, list) else raw.get("labels", []):
        addr = row.get("address")
        if not addr:
            continue
        cat = _infer_category(str(row.get("label") or row.get("tag") or ""))
        labels.append(
            EntityLabel(
                address=addr,
                chain="tron",
                label=str(row.get("label") or row.get("tag")),
                category=cat,
                confidence=float(row.get("confidence") or 0.75),
                source="tronscan",
                tier=TIER_OPEN_DATASET,
                risk_score=_category_risk(cat),
                evidence="tronscan:seed",
            )
        )
    return labels


def _labels_from_json(
    path: Path,
    *,
    source: str,
    tier: int,
    sanctioned: bool,
) -> list[EntityLabel]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: list[EntityLabel] = []
    for row in raw:
        out.append(
            EntityLabel(
                address=row["address"],
                chain=row["chain"],
                label=row.get("label") or source,
                category=row.get("category") or "sanctions",
                confidence=float(row.get("confidence") or 0.9),
                source=source,
                tier=tier,
                risk_score=float(row.get("risk_score") or 90),
                sanctioned=sanctioned,
                evidence=row.get("evidence"),
            )
        )
    return out


def _infer_chain_addr(value: str) -> tuple[str | None, str | None]:
    v = value.strip()
    if v.startswith("0x") and len(v) >= 42:
        return "eth", v.lower()[:42]
    if v.startswith("T") and len(v) == 34:
        return "tron", v
    if re.fullmatch(r"([13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-z0-9]{39,59})", v):
        return "btc", v
    return None, None


def _infer_category(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ("binance", "okx", "bybit", "kraken", "huobi", "htx", "exchange", "hot wallet")):
        return "exchange"
    if any(k in n for k in ("gambling", "casino", "bet", "stake", "bc.game", "shuffle")):
        return "gambling"
    if any(k in n for k in ("sanction", "ofac", "mixer", "tornado")):
        return "sanctions"
    return "other"


def _category_risk(category: str) -> float:
    return {
        "sanctions": 95.0,
        "gambling": 70.0,
        "exchange": 12.0,
        "payment": 10.0,
        "other": 20.0,
    }.get(category, 25.0)
