from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from flowsint_crypto_compliance.detection.findings import IllegalFlowFinding
from flowsint_types.fiat_crypto import FiatCryptoBridge, FusedAttribution

FEATURE_NAMES: tuple[str, ...] = (
    "critical_findings",
    "high_findings",
    "medium_findings",
    "sanctioned_wallets",
    "black_zone_wallets",
    "gray_zone_wallets",
    "bank_links",
    "offshore_bridges",
    "layering_bridges",
    "avg_confidence",
    "max_linkage",
    "registry_hits",
    "mixer_signals",
    "wallet_count",
    "bridge_count",
)


@dataclass(frozen=True)
class RiskModelResult:
    score: float
    heuristic_score: float
    model_score: float
    model_version: str
    features: dict[str, float]


class SovereignRiskModel:
    """
    XGBoost risk scorer for 115-ФЗ typologies.

    Uses a compact regressor trained on deterministic synthetic typology vectors.
    Production deployments can replace the bundled model via `model_path`.
    """

    MODEL_VERSION = "sovereign-xgb-v1"

    def __init__(self, *, model_path: str | None = None) -> None:
        self._model = _load_or_train_model(model_path)

    def score_case(
        self,
        *,
        findings: Sequence[IllegalFlowFinding],
        attributions: Sequence[FusedAttribution],
        bridges: Sequence[FiatCryptoBridge],
        bank_feed_count: int = 0,
        control_purchase_count: int = 0,
        heuristic_score: float,
    ) -> RiskModelResult:
        features = extract_case_features(
            findings=findings,
            attributions=attributions,
            bridges=bridges,
            bank_feed_count=bank_feed_count,
            control_purchase_count=control_purchase_count,
        )
        vector = np.array([[features[name] for name in FEATURE_NAMES]], dtype=np.float32)
        model_score = float(np.clip(self._model.predict(vector)[0], 0.0, 100.0))
        blended = round(min(100.0, 0.55 * heuristic_score + 0.45 * model_score), 1)
        return RiskModelResult(
            score=blended,
            heuristic_score=round(heuristic_score, 1),
            model_score=round(model_score, 1),
            model_version=self.MODEL_VERSION,
            features=features,
        )

    def score_wallet(
        self,
        *,
        findings: Sequence[dict[str, Any]],
        risk_score_hint: float | None,
        sanctioned: bool,
        counterparty_hits: int,
        onchain_hops: int,
        heuristic_score: float,
    ) -> RiskModelResult:
        features = extract_wallet_features(
            findings=findings,
            risk_score_hint=risk_score_hint,
            sanctioned=sanctioned,
            counterparty_hits=counterparty_hits,
            onchain_hops=onchain_hops,
        )
        vector = np.array([[features[name] for name in FEATURE_NAMES]], dtype=np.float32)
        model_score = float(np.clip(self._model.predict(vector)[0], 0.0, 100.0))
        if sanctioned:
            model_score = max(model_score, 96.0)
        blended = round(min(100.0, 0.5 * heuristic_score + 0.5 * model_score), 1)
        return RiskModelResult(
            score=blended,
            heuristic_score=round(heuristic_score, 1),
            model_score=round(model_score, 1),
            model_version=self.MODEL_VERSION,
            features=features,
        )


def extract_case_features(
    *,
    findings: Sequence[IllegalFlowFinding],
    attributions: Sequence[FusedAttribution],
    bridges: Sequence[FiatCryptoBridge],
    bank_feed_count: int,
    control_purchase_count: int,
) -> dict[str, float]:
    offshore = {"AE", "TR", "DO", "PA", "SC", "VG", "CY", "SG", "HK", "US", "EU"}
    linkages = [a.linkage_strength for a in attributions if a.linkage_strength is not None]
    return {
        "critical_findings": float(sum(1 for f in findings if f.severity == "critical")),
        "high_findings": float(sum(1 for f in findings if f.severity == "high")),
        "medium_findings": float(sum(1 for f in findings if f.severity == "medium")),
        "sanctioned_wallets": float(sum(1 for a in attributions if a.sanctioned)),
        "black_zone_wallets": float(sum(1 for a in attributions if a.black_zone)),
        "gray_zone_wallets": float(sum(1 for a in attributions if a.gray_zone)),
        "bank_links": float(sum(1 for a in attributions if (a.linkage_strength or 0) >= 0.5)),
        "offshore_bridges": float(
            sum(
                1
                for b in bridges
                if (b.region_destination or "").upper() in offshore
            )
        ),
        "layering_bridges": float(sum(1 for b in bridges if (b.hop_count or 0) >= 3)),
        "avg_confidence": float(np.mean([a.confidence for a in attributions]) if attributions else 0.0),
        "max_linkage": float(max(linkages) if linkages else 0.0),
        "registry_hits": float(sum(1 for a in attributions if a.watchlist_label)),
        "mixer_signals": float(sum(1 for f in findings if f.code in {"MIXER_EXPOSURE", "SANCTIONS_LIST_HIT"})),
        "wallet_count": float(len(attributions)),
        "bridge_count": float(len(bridges)),
    }


def extract_wallet_features(
    *,
    findings: Sequence[dict[str, Any]],
    risk_score_hint: float | None,
    sanctioned: bool,
    counterparty_hits: int,
    onchain_hops: int,
) -> dict[str, float]:
    severities = [str(f.get("severity", "")) for f in findings]
    codes = [str(f.get("code", "")) for f in findings]
    return {
        "critical_findings": float(sum(1 for s in severities if s == "critical")),
        "high_findings": float(sum(1 for s in severities if s == "high")),
        "medium_findings": float(sum(1 for s in severities if s == "medium")),
        "sanctioned_wallets": 1.0 if sanctioned else 0.0,
        "black_zone_wallets": float("HIGH_FAN_IN_OUT" in codes),
        "gray_zone_wallets": float(any(c.startswith("REGISTRY_") for c in codes)),
        "bank_links": 0.0,
        "offshore_bridges": 0.0,
        "layering_bridges": float(onchain_hops >= 10),
        "avg_confidence": float(
            np.mean([float(f.get("confidence", 0.5)) for f in findings]) if findings else 0.0
        ),
        "max_linkage": 0.0,
        "registry_hits": float(any(c.startswith("REGISTRY_") or c == "SANCTIONS_LIST_HIT" for c in codes)),
        "mixer_signals": float(any(c in {"SANCTIONS_LIST_HIT", "REGISTRY_HIGH_RISK_LABEL"} for c in codes)),
        "wallet_count": 1.0,
        "bridge_count": float(counterparty_hits),
    }


def _load_or_train_model(model_path: str | None):
    import xgboost as xgb

    if model_path:
        model = xgb.XGBRegressor()
        model.load_model(model_path)
        return model
    global _default_model
    if _default_model is None:
        _default_model = _train_default_model()
    return _default_model


_default_model = None


def _train_default_model():
    import xgboost as xgb

    rng = np.random.default_rng(42)
    rows: list[list[float]] = []
    targets: list[float] = []

    for _ in range(400):
        features = {
            "critical_findings": float(rng.integers(0, 4)),
            "high_findings": float(rng.integers(0, 6)),
            "medium_findings": float(rng.integers(0, 8)),
            "sanctioned_wallets": float(rng.integers(0, 2)),
            "black_zone_wallets": float(rng.integers(0, 3)),
            "gray_zone_wallets": float(rng.integers(0, 5)),
            "bank_links": float(rng.integers(0, 4)),
            "offshore_bridges": float(rng.integers(0, 3)),
            "layering_bridges": float(rng.integers(0, 4)),
            "avg_confidence": float(rng.uniform(0.2, 1.0)),
            "max_linkage": float(rng.uniform(0.0, 1.0)),
            "registry_hits": float(rng.integers(0, 5)),
            "mixer_signals": float(rng.integers(0, 3)),
            "wallet_count": float(rng.integers(1, 12)),
            "bridge_count": float(rng.integers(0, 6)),
        }
        rows.append([features[name] for name in FEATURE_NAMES])
        targets.append(_synthetic_target(features))

    model = xgb.XGBRegressor(
        n_estimators=80,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="reg:squarederror",
        random_state=42,
    )
    model.fit(np.array(rows, dtype=np.float32), np.array(targets, dtype=np.float32))
    return model


def _synthetic_target(features: dict[str, float]) -> float:
    score = (
        features["critical_findings"] * 28
        + features["high_findings"] * 16
        + features["medium_findings"] * 7
        + features["sanctioned_wallets"] * 35
        + features["black_zone_wallets"] * 18
        + features["bank_links"] * 10
        + features["offshore_bridges"] * 14
        + features["layering_bridges"] * 8
        + features["registry_hits"] * 6
        + features["mixer_signals"] * 20
        + features["max_linkage"] * 12
        + features["avg_confidence"] * 10
    )
    return float(min(100.0, score))
