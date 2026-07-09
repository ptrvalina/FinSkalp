"""RFC-0006 Fusion Intelligence — Ch.3."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.intelligence_engine.pipeline import FUSION_INTELLIGENCE_STAGES


def run_fusion_intelligence(
    records: list[dict[str, Any]],
    *,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Enrich raw records with fusion dimensions before KG ingest."""
    ctx = context or {}
    enriched: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    conflicts: list[dict[str, Any]] = []

    for i, rec in enumerate(records):
        if not isinstance(rec, dict):
            continue
        row = dict(rec)
        content_key = f"{row.get('source_type')}:{row.get('entity_value') or row.get('mention')}"
        is_dup = content_key in seen_hashes
        seen_hashes.add(content_key)

        trust = float(row.get("confidence") or row.get("fusion_confidence") or 0.5)
        row["_fusion"] = {
            "source": row.get("source_type") or "unknown",
            "type": row.get("entity_type") or "mention",
            "trust": trust,
            "relations": row.get("relations") or [],
            "conflicts": [],
            "duplicate": is_dup,
            "priority": _priority(trust, row),
            "context": {"case_ref": ctx.get("case_ref")},
            "impact": min(1.0, trust + (0.1 if not is_dup else 0)),
            "entity": row.get("entity_value") or row.get("mention"),
            "evidence": bool(row.get("evidence_id") or row.get("snapshot_uri")),
            "graph": True,
        }
        if is_dup:
            conflicts.append({"index": i, "key": content_key})
            row["_fusion"]["conflicts"].append("duplicate_source")
        enriched.append(row)

    return {
        "stages": FUSION_INTELLIGENCE_STAGES,
        "records": enriched,
        "conflict_count": len(conflicts),
        "duplicate_count": sum(1 for r in enriched if r.get("_fusion", {}).get("duplicate")),
        "explain_ru": "Fusion определил источник, тип, достоверность, связи и приоритет каждого факта",
    }


def _priority(trust: float, row: dict[str, Any]) -> str:
    if trust >= 0.85 or row.get("category") in ("sanctions", "mixer"):
        return "critical"
    if trust >= 0.65:
        return "high"
    if trust >= 0.4:
        return "medium"
    return "low"
