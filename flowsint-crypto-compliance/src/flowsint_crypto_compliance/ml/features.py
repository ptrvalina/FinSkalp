"""Feature vectors for ML risk scoring (XGBoost / GraphSAGE input)."""

from __future__ import annotations

from typing import Any

import numpy as np

from flowsint_crypto_compliance.osint_core.evidence_graph import EvidenceGraph, NodeKind

FEATURE_NAMES = [
    "mention_count",
    "independent_source_types",
    "avg_confidence",
    "max_confidence",
    "high_risk_tag_count",
    "graph_degree",
    "graph_betweenness",
    "graphsage_embedding_0",
    "graphsage_embedding_1",
    "graphsage_embedding_2",
]

_HIGH_RISK_TAGS = frozenset(
    {
        "mixer_like",
        "scam_report",
        "sanctions_screening",
        "enforcement_seizure",
        "otc_gray",
        "enforcement_context",
    }
)


def extract_mention_features(mentions: list[Any]) -> dict[str, float]:
    if not mentions:
        return {name: 0.0 for name in FEATURE_NAMES}

    confs = [float(getattr(m, "confidence", 0.5)) for m in mentions]
    source_types = {getattr(m, "source_type", "") for m in mentions}
    tags = {getattr(m, "risk_tag", "") for m in mentions}
    high_risk = len(tags & _HIGH_RISK_TAGS)

    base = {
        "mention_count": float(len(mentions)),
        "independent_source_types": float(len(source_types)),
        "avg_confidence": float(sum(confs) / len(confs)),
        "max_confidence": float(max(confs)),
        "high_risk_tag_count": float(high_risk),
    }
    for name in FEATURE_NAMES:
        base.setdefault(name, 0.0)
    return base


def merge_graph_features(
    mention_features: dict[str, float],
    graph: EvidenceGraph | None,
    *,
    wallet_primary_key: str | None = None,
) -> np.ndarray:
    from flowsint_crypto_compliance.ml.graphsage import graph_metrics_and_embedding

    metrics = graph_metrics_and_embedding(graph, wallet_primary_key=wallet_primary_key)
    merged = {**mention_features, **metrics}
    return np.array([merged.get(name, 0.0) for name in FEATURE_NAMES], dtype=np.float32)
