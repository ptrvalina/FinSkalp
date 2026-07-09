"""Tests for KYT import (MetaSleuth / BlockSec style)."""

from __future__ import annotations

import json
from pathlib import Path

from flowsint_crypto_compliance.ingestion.kyt_import import import_kyt_bundle, parse_kyt_file
from flowsint_crypto_compliance.storage.kyt_exposure_store import get_exposure, put_exposure
from flowsint_crypto_compliance.storage.label_cache import LabelCache


def test_parse_kyt_exposure_bundle(tmp_path: Path):
    data = {
        "focus_address": "TZASfRXk51No5XHPDE2eCcXpS8F8t1jgwL",
        "chain": "tron",
        "exposure_rows": [
            {
                "entity_name": "Bybit",
                "category": "exchange",
                "risk_pct": 10,
                "hops": 2,
                "amount": 4000.0,
                "behavior": "indirect",
                "risk_tier": "low",
            }
        ],
    }
    path = tmp_path / "sample.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    bundle = parse_kyt_file(path)
    assert bundle["focus_address"] == data["focus_address"]
    assert len(bundle["exposure_rows"]) == 1
    assert bundle["exposure_rows"][0]["entity_name"] == "Bybit"


def test_import_kyt_bundle_puts_labels(tmp_path: Path):
    rows = [
        {
            "address": "TZASfRXk51No5XHPDE2eCcXpS8F8t1jgwL",
            "entity_name": "Bybit",
            "category": "exchange",
            "chain": "tron",
            "risk_score": 15,
        }
    ]
    path = tmp_path / "labels.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    bundle = parse_kyt_file(path)
    cache = LabelCache()
    stats = import_kyt_bundle(cache, bundle)
    assert stats["labels_imported"] >= 1
    assert cache.count() >= 1


def test_exposure_store_roundtrip():
    put_exposure("tron", "TAddr123", [{"entity_name": "Binance", "amount": 100}])
    rows = get_exposure("tron", "TAddr123")
    assert rows[0]["entity_name"] == "Binance"
