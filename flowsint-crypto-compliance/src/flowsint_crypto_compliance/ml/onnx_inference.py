"""ONNX Runtime inference for risk scoring."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np

from flowsint_crypto_compliance.ml.features import FEATURE_NAMES, merge_graph_features

_MODEL_ENV = "FINSKALP_ML_MODEL_PATH"


def default_model_path() -> Path:
    env = os.getenv(_MODEL_ENV)
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[1] / "data" / "models" / "risk_xgb.onnx"


class ONNXRiskScorer:
    def __init__(self, model_path: Path | None = None) -> None:
        self._path = model_path or default_model_path()
        self._session = None
        self._available = False
        self._try_load()

    def _try_load(self) -> None:
        if not self._path.is_file():
            return
        try:
            import onnxruntime as ort

            self._session = ort.InferenceSession(
                str(self._path), providers=["CPUExecutionProvider"]
            )
            self._available = True
        except Exception:
            self._session = None
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def score(
        self,
        mentions: list[Any],
        *,
        graph: Any = None,
        wallet_primary_key: str | None = None,
    ) -> dict[str, Any]:
        from flowsint_crypto_compliance.ml.features import extract_mention_features

        mention_feats = extract_mention_features(mentions)
        vector = merge_graph_features(mention_feats, graph, wallet_primary_key=wallet_primary_key)

        if not self._available or self._session is None:
            return {
                "score": float(_heuristic_from_vector(vector)),
                "backend": "heuristic",
                "model_path": str(self._path),
                "features": dict(zip(FEATURE_NAMES, vector.tolist())),
            }

        input_name = self._session.get_inputs()[0].name
        proba = self._session.run(None, {input_name: vector.reshape(1, -1)})[0]
        illicit_prob = float(proba[0][1]) if proba.ndim == 2 and proba.shape[1] > 1 else float(proba[0])
        return {
            "score": round(illicit_prob * 100.0, 1),
            "backend": "onnx",
            "model_path": str(self._path),
            "illicit_probability": round(illicit_prob, 4),
            "features": dict(zip(FEATURE_NAMES, vector.tolist())),
        }


def _heuristic_from_vector(vector: np.ndarray) -> float:
    if vector.sum() == 0:
        return 0.0
    weights = np.array([0.08, 0.12, 0.15, 0.12, 0.18, 0.1, 0.08, 0.06, 0.06, 0.05], dtype=np.float32)
    raw = float(np.dot(vector[: len(weights)], weights))
    return min(100.0, raw * 8.0)
