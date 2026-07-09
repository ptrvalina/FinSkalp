"""Unified ML scoring pipeline (ONNX XGBoost + GraphSAGE features)."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from flowsint_crypto_compliance.ml.onnx_inference import ONNXRiskScorer


@lru_cache(maxsize=1)
def get_risk_scorer() -> ONNXRiskScorer:
    return ONNXRiskScorer()


def score_risk(
    address: str,
    chain: str,
    mentions: list[Any],
    *,
    graph: Any = None,
    wallet_primary_key: str | None = None,
) -> dict[str, Any]:
    scorer = get_risk_scorer()
    wallet_key = wallet_primary_key or f"{chain}:{address}"
    result = scorer.score(mentions, graph=graph, wallet_primary_key=wallet_key)
    result["address"] = address
    result["chain"] = chain
    return result


def ml_risk_score(
    address: str,
    chain: str,
    mentions: list[Any],
    *,
    graph: Any = None,
    graph_features: dict[str, float] | None = None,
) -> float:
    """Backward-compatible float score for ScalpelEngine."""
    out = score_risk(address, chain, mentions, graph=graph)
    return float(out["score"])


def score_fusion_graph(
    fusion_graph: dict[str, Any],
    *,
    address: str,
    chain: str,
) -> dict[str, Any]:
    """Score multi-hop fusion graph (nodes/edges/risk_annotations)."""
    from flowsint_crypto_compliance.ml.features import extract_mention_features

    ann_count = len(fusion_graph.get("risk_annotations") or [])
    illicit_count = sum(
        1 for a in fusion_graph.get("risk_annotations") or [] if a.get("type") == "illicit_hit"
    )
    pseudo_mentions = [
        type("M", (), {"confidence": 0.8, "source_type": "sanctions", "risk_tag": "sanctions_screening"})()
        for _ in range(illicit_count)
    ]
    mention_feats = extract_mention_features(pseudo_mentions)
    mention_feats["mention_count"] = float(len(fusion_graph.get("nodes") or []))
    mention_feats["graph_degree"] = float(len(fusion_graph.get("edges") or []))
    mention_feats["high_risk_tag_count"] = float(illicit_count)
    if fusion_graph.get("corridor_flagged"):
        mention_feats["high_risk_tag_count"] += 2.0

    from flowsint_crypto_compliance.ml.onnx_inference import ONNXRiskScorer
    import numpy as np
    from flowsint_crypto_compliance.ml.features import FEATURE_NAMES, merge_graph_features

    vector = merge_graph_features(mention_feats, None)
    scorer = ONNXRiskScorer()
    if scorer.available:
        input_name = scorer._session.get_inputs()[0].name
        proba = scorer._session.run(None, {input_name: vector.reshape(1, -1)})[0]
        illicit_prob = float(proba[0][1]) if proba.ndim == 2 and proba.shape[1] > 1 else float(proba[0])
        score = round(illicit_prob * 100.0, 1)
        backend = "onnx"
    else:
        score = round(min(100.0, illicit_count * 25 + ann_count * 10 + len(fusion_graph.get("edges") or []) * 2), 1)
        backend = "heuristic"

    return {
        "score": score,
        "backend": backend,
        "illicit_nodes": illicit_count,
        "corridor_flagged": fusion_graph.get("corridor_flagged", False),
        "address": address,
        "chain": chain,
    }
