"""Shared in-memory context for demo stand (no PostgreSQL / Neo4j required)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from flowsint_crypto_compliance.demo.chain_data import get_demo_adapters
from flowsint_crypto_compliance.demo.scenarios import SCENARIOS
from flowsint_crypto_compliance.ingestion.kyt_import import import_kyt_bundle, parse_kyt_file
from flowsint_crypto_compliance.storage.kyt_exposure_store import put_exposure
from flowsint_crypto_compliance.storage.label_cache import LabelCache

_label_cache: LabelCache | None = None
_seeded = False
_kyt_preloaded = False


def get_demo_label_cache() -> LabelCache:
    global _label_cache, _seeded
    if _label_cache is None:
        _label_cache = LabelCache()
    if not _seeded:
        seed_demo_registry(_label_cache)
        _seeded = True
    return _label_cache


def seed_demo_registry(cache: LabelCache | None = None) -> int:
    """Load sovereign registry labels from all demo scenarios."""
    global _seeded
    target = cache or get_demo_label_cache()
    count = 0
    for scenario in SCENARIOS.values():
        for label in scenario.registry_labels:
            target.put(label)
            count += 1
    _seeded = True
    return count


def preload_kyt_samples(cache: LabelCache | None = None) -> int:
    """Load optional KYT samples (MetaSleuth-style exposure) for combat demo addresses."""
    global _kyt_preloaded
    if _kyt_preloaded:
        return 0
    if os.getenv("FINSKALP_KYT_SAMPLES", "").strip().lower() in {"0", "false", "no"}:
        _kyt_preloaded = True
        return 0
    if (
        os.getenv("COMPLIANCE_COMBAT_MODE", "1").strip().lower() in {"1", "true", "yes"}
        and os.getenv("FINSKALP_KYT_SAMPLES", "").strip() == ""
    ):
        _kyt_preloaded = True
        return 0

    target = cache or get_demo_label_cache()
    samples_dir = Path(__file__).resolve().parents[1] / "data" / "kyt_samples"
    loaded = 0
    if samples_dir.is_dir():
        for path in sorted(samples_dir.glob("*.json")):
            try:
                bundle = parse_kyt_file(path)
                import_kyt_bundle(target, bundle)
                focus = bundle.get("focus_address")
                chain = bundle.get("chain", "tron")
                rows = bundle.get("exposure_rows") or []
                if focus and rows:
                    put_exposure(chain, focus, rows)
                loaded += 1
            except Exception:
                continue

    extra_dir = os.getenv("FINSKALP_KYT_LABELS_DIR")
    if extra_dir:
        for path in Path(extra_dir).glob("*"):
            if path.suffix.lower() in {".json", ".jsonl", ".csv", ".xlsx"}:
                try:
                    bundle = parse_kyt_file(path)
                    import_kyt_bundle(target, bundle)
                    focus = bundle.get("focus_address")
                    if focus and bundle.get("exposure_rows"):
                        put_exposure(bundle.get("chain", "tron"), focus, bundle["exposure_rows"])
                    loaded += 1
                except Exception:
                    continue

    _kyt_preloaded = True
    return loaded


def get_demo_chain_adapters(scenario_id: str | None = None):
    return get_demo_adapters(scenario_id)
