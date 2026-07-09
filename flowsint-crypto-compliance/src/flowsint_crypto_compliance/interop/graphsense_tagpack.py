"""GraphSense TagPack CSV loader (lightweight, no GraphSense server)."""

from __future__ import annotations

import csv
import io
import logging
import os
from pathlib import Path
from typing import Any

import httpx

from flowsint_crypto_compliance.attribution.types import TIER_OPEN_DATASET, EntityLabel

_log = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "attribution"
_DEFAULT_TAGPACK = _DATA_DIR / "graphsense_tagpack.csv"
_TAGPACK_URL = os.getenv("FINSKALP_GRAPHSENSE_TAGPACK_URL", "")

_CURRENCY_TO_CHAIN = {
    "trx": "tron",
    "tron": "tron",
    "eth": "eth",
    "btc": "btc",
    "bnb": "bsc",
}


def _chain_from_row(row: dict[str, str]) -> str | None:
    if row.get("chain"):
        return row["chain"].strip().lower()
    currency = (row.get("currency") or "").strip().lower()
    if currency:
        return _CURRENCY_TO_CHAIN.get(currency, currency)
    return None


def _parse_tagpack_text(text: str) -> list[EntityLabel]:
    labels: list[EntityLabel] = []
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return labels

    # GraphSense TagPack: address,currency,label (+ optional category)
    for row in reader:
        norm = {k.lower().strip(): (v or "").strip() for k, v in row.items()}
        addr = norm.get("address") or ""
        if not addr:
            continue
        chain = _chain_from_row(norm)
        if not chain:
            continue
        label_text = norm.get("label") or norm.get("entity") or "GraphSense"
        category = (norm.get("category") or "exchange").lower()
        confidence = float(norm.get("confidence") or 0.8)
        risk = float(norm.get("risk_score") or 15.0)
        labels.append(
            EntityLabel(
                address=addr,
                chain=chain,
                label=label_text,
                category=category,
                confidence=confidence,
                source="graphsense",
                tier=TIER_OPEN_DATASET,
                risk_score=risk,
                evidence="graphsense:tagpack",
            )
        )
    return labels


def parse_tagpack_csv(text: str) -> list[EntityLabel]:
    """Public alias for TagPack CSV parsing (upload API)."""
    return _parse_tagpack_text(text)


def load_tagpack(path: str | Path | None = None) -> list[EntityLabel]:
    """Load TagPack CSV from path (default: bundled tagpack)."""
    p = Path(path) if path else _DEFAULT_TAGPACK
    if not p.is_file():
        return []
    return _parse_tagpack_text(p.read_text(encoding="utf-8"))


async def load_tagpack_from_url(url: str | None = None) -> list[EntityLabel]:
    """Fetch TagPack CSV from URL (optional remote source)."""
    target = (url or _TAGPACK_URL).strip()
    if not target:
        return []
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(target)
        if resp.status_code != 200:
            _log.warning("GraphSense tagpack URL HTTP %s", resp.status_code)
            return []
        return _parse_tagpack_text(resp.text)
    except Exception as exc:
        _log.warning("GraphSense tagpack fetch failed: %s", exc)
        return []


async def bootstrap_tagpack() -> list[EntityLabel]:
    """Bundled tagpack + optional URL import."""
    labels = load_tagpack()
    if _TAGPACK_URL:
        remote = await load_tagpack_from_url()
        seen = {(l.chain, l.address) for l in labels}
        for lbl in remote:
            key = (lbl.chain, lbl.address)
            if key not in seen:
                labels.append(lbl)
                seen.add(key)
    return labels


def tagpack_stats(labels: list[EntityLabel]) -> dict[str, Any]:
    by_chain: dict[str, int] = {}
    for lbl in labels:
        by_chain[lbl.chain] = by_chain.get(lbl.chain, 0) + 1
    return {"count": len(labels), "by_chain": by_chain}
