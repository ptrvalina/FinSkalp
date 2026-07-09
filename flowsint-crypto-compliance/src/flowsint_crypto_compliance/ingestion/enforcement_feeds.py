"""
Ingest публичных enforcement notices: DOJ + Europol RSS.

Только официальные пресс-релизы; извлечение крипто-адресов regex.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import httpx

_STORE = Path(__file__).resolve().parents[1] / "data" / "enforcement_seizures.json"

_BTC_RE = re.compile(r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b")
_ETH_RE = re.compile(r"\b0x[a-fA-F0-9]{40}\b")
_TRON_RE = re.compile(r"\bT[1-9A-HJ-NP-Za-km-z]{33}\b")

_FEEDS = (
    {
        "source": "DOJ",
        "url": "https://www.justice.gov/feeds/opa/justice-news.xml",
    },
    {
        "source": "Europol",
        "url": "https://www.europol.europa.eu/rss",
    },
)

_CRYPTO_KEYWORDS = re.compile(
    r"(?i)(bitcoin|crypto|cryptocurrency|virtual currency|seizure|seized|blockchain|wallet)"
)


@dataclass
class EnforcementRecord:
    record_id: str
    source: str
    title: str
    url: str
    published_at: str | None
    excerpt: str
    addresses: list[dict[str, str]] = field(default_factory=list)
    ingested_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _extract_addresses(text: str) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    seen: set[str] = set()
    for chain, pattern in (("btc", _BTC_RE), ("eth", _ETH_RE), ("tron", _TRON_RE)):
        for match in pattern.findall(text):
            if match in seen:
                continue
            seen.add(match)
            found.append({"chain": chain, "address": match})
    return found


def _parse_rss(xml_text: str, *, source: str) -> list[EnforcementRecord]:
    root = ElementTree.fromstring(xml_text)
    items = root.findall(".//item") or root.findall(".//{*}item")
    records: list[EnforcementRecord] = []

    for item in items:
        title = (item.findtext("title") or item.findtext("{*}title") or "").strip()
        link = (item.findtext("link") or item.findtext("{*}link") or "").strip()
        pub = item.findtext("pubDate") or item.findtext("{*}pubDate")
        desc = (
            item.findtext("description")
            or item.findtext("{*}description")
            or item.findtext("content:encoded")
            or ""
        )
        blob = f"{title} {desc}"
        if not _CRYPTO_KEYWORDS.search(blob):
            continue
        addresses = _extract_addresses(blob)
        if not addresses and "seiz" not in blob.lower():
            continue
        rid = f"{source}:{hash(link or title) & 0xFFFFFFFF:08x}"
        records.append(
            EnforcementRecord(
                record_id=rid,
                source=source,
                title=title[:500],
                url=link,
                published_at=pub,
                excerpt=desc[:2000],
                addresses=addresses,
            )
        )
    return records


def ingest_enforcement_feeds(*, timeout: float = 20.0) -> dict[str, Any]:
    all_records: list[EnforcementRecord] = []
    feed_status: dict[str, str] = {}

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        for feed in _FEEDS:
            try:
                resp = client.get(feed["url"])
                if resp.status_code != 200:
                    feed_status[feed["source"]] = f"http_{resp.status_code}"
                    continue
                parsed = _parse_rss(resp.text, source=feed["source"])
                all_records.extend(parsed)
                feed_status[feed["source"]] = f"ok:{len(parsed)}"
            except Exception as exc:
                feed_status[feed["source"]] = f"error:{exc.__class__.__name__}"

    merged = _merge_store(all_records)
    _save_store(merged)
    return {
        "ingested_new": len(all_records),
        "total_records": len(merged),
        "feeds": feed_status,
        "store_path": str(_STORE),
    }


def _merge_store(new_records: list[EnforcementRecord]) -> list[dict[str, Any]]:
    existing = load_enforcement_store()
    by_id = {r["record_id"]: r for r in existing}
    for rec in new_records:
        by_id[rec.record_id] = rec.to_dict()
    return list(by_id.values())


def load_enforcement_store() -> list[dict[str, Any]]:
    if not _STORE.is_file():
        return []
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_store(records: list[dict[str, Any]]) -> None:
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def lookup_address(address: str, chain: str) -> list[dict[str, Any]]:
    norm = address.lower() if chain == "eth" else address
    hits: list[dict[str, Any]] = []
    for row in load_enforcement_store():
        for addr in row.get("addresses") or []:
            a = addr.get("address", "")
            c = addr.get("chain", "")
            key = a.lower() if c == "eth" else a
            if key == norm and c == chain:
                hits.append(row)
                break
    return hits
