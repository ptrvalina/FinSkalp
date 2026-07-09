"""Shared analysis helpers for RFC-0004 intelligence engines."""

from __future__ import annotations

from typing import Any

MIXER_KEYWORDS = frozenset({"mixer", "tornado", "blender", "cyclone", "sanctions", "scam", "ransomware"})
BRIDGE_KEYWORDS = frozenset({"bridge", "cross-chain", "wormhole", "layerzero", "multichain"})


def detect_mixer_signals(attribution: dict[str, Any], screening: dict[str, Any]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    labels = (attribution or {}).get("labels") or {}
    for addr, lbl in labels.items():
        if not isinstance(lbl, dict):
            continue
        cat = str(lbl.get("category") or "").lower()
        label = str(lbl.get("label") or "").lower()
        if cat in MIXER_KEYWORDS or any(k in label for k in MIXER_KEYWORDS):
            hits.append({"address": addr, "category": cat, "label": lbl.get("label"), "confidence": lbl.get("confidence", 0.8)})
    findings = (screening or {}).get("findings") or []
    for f in findings:
        if not isinstance(f, dict):
            continue
        code = str(f.get("code") or "").upper()
        if "MIXER" in code or "SANCTION" in code:
            hits.append({"code": code, "confidence": f.get("confidence", 0.85), "title": f.get("title_ru")})
    return hits


def detect_bridge_signals(screening: dict[str, Any], attribution: dict[str, Any]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    onchain = (screening or {}).get("onchain_summary") or {}
    bridges = onchain.get("bridges") or screening.get("bridges") or []
    if isinstance(bridges, list):
        for b in bridges:
            if isinstance(b, dict):
                hits.append({"type": "bridge", **b})
    exposure = (attribution or {}).get("exposure") or {}
    for conn in exposure.get("connections") or []:
        if not isinstance(conn, dict):
            continue
        tag = str(conn.get("tag") or conn.get("category") or "").lower()
        if any(k in tag for k in BRIDGE_KEYWORDS):
            hits.append({"type": "bridge_connection", **conn})
    return hits


def cluster_hints(screening: dict[str, Any], attribution: dict[str, Any]) -> list[dict[str, Any]]:
    hints: list[dict[str, Any]] = []
    clusters = (screening or {}).get("clusters") or attribution.get("clusters") or []
    if isinstance(clusters, list):
        for c in clusters:
            if isinstance(c, dict) and c.get("cluster_id"):
                hints.append(c)
    exposure = (attribution or {}).get("exposure") or {}
    if int(exposure.get("connection_count") or 0) >= 3:
        hints.append(
            {
                "cluster_id": "exposure_cluster",
                "member_count": exposure.get("connection_count"),
                "confidence": 0.65,
            }
        )
    return hints


def corridor_hints(screening: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        from flowsint_crypto_compliance.engine.corridor_analyzer import CorridorAnalyzer

        regions = (screening or {}).get("regions") or (screening or {}).get("observed_regions") or []
        if not regions:
            geo = (screening or {}).get("geo_signals") or []
            regions = [g.get("region") for g in geo if isinstance(g, dict) and g.get("region")]
        if len(regions) < 2:
            return []
        return [
            {
                "corridor": list(m.corridor),
                "matched_regions": m.matched_regions,
                "confidence": m.confidence,
                "coverage": m.coverage,
            }
            for m in CorridorAnalyzer().match([str(r) for r in regions])
        ]
    except Exception:
        return []


def temporal_correlation_signals(mentions: list[dict[str, Any]], *, window_hours: float = 72.0) -> list[dict[str, Any]]:
    """Find OSINT mentions clustered in time."""
    from datetime import datetime, timezone

    stamps: list[datetime] = []
    for m in mentions:
        if not isinstance(m, dict):
            continue
        raw = m.get("timestamp") or m.get("discovered_at") or m.get("occurred_at")
        if not raw:
            continue
        try:
            ts = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            stamps.append(ts)
        except ValueError:
            continue
    if len(stamps) < 2:
        return []
    stamps.sort()
    span_h = (stamps[-1] - stamps[0]).total_seconds() / 3600.0
    if span_h <= window_hours:
        return [
            {
                "code": "TEMPORAL_CLUSTER",
                "mention_count": len(stamps),
                "span_hours": round(span_h, 2),
                "confidence": min(0.9, 0.5 + len(stamps) * 0.05),
            }
        ]
    return []


def illegal_flow_risk_boost(screening: dict[str, Any], attribution: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    """Delegate to IllegalFlowDetector when attribution data present."""
    try:
        from flowsint_crypto_compliance.attribution.attribution_engine import AttributionResult
        from flowsint_crypto_compliance.detection.illegal_flow import IllegalFlowDetector

        attr = AttributionResult.from_dict(attribution)
        bridges = screening.get("bridges") or []
        if not isinstance(bridges, list):
            bridges = []
        detector = IllegalFlowDetector(use_xgboost=False)
        findings, score, explain = detector.analyze(
            attributions=[],
            bridges=bridges,
            bank_feed_count=int(screening.get("bank_feed_count") or 0),
            control_purchase_count=int(screening.get("control_purchase_count") or 0),
        )
        if attr.labels:
            findings2, score2, explain2 = detector.analyze(
                attributions=[],
                bridges=bridges,
            )
            score = max(score, score2)
            explain = {**explain, **explain2}
        return float(score), {"findings": [f.code for f in findings], **explain}
    except Exception:
        return 0.0, {}
