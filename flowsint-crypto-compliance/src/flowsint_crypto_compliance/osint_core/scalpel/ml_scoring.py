"""ML scoring — delegates to ONNX + GraphSAGE pipeline."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.ml.scoring_pipeline import ml_risk_score, score_risk

__all__ = ["baseline_ml_score", "score_risk", "ml_risk_score"]


def baseline_ml_score(
    address: str,
    chain: str,
    mentions: list[Any],
    *,
    graph: Any = None,
    graph_features: dict[str, float] | None = None,
) -> float:
    return ml_risk_score(address, chain, mentions, graph=graph, graph_features=graph_features)
