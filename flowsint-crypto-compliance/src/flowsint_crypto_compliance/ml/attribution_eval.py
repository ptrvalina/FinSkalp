"""Attribution engine evaluation — precision/recall, drift (Evidently AI)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

REPORT_DIR = Path(os.getenv("FINSKALP_EVAL_REPORT_DIR", "reports/attribution_eval"))
BASELINE_FILE = REPORT_DIR / "baseline_metrics.json"

POSITIVE_SOURCES = frozenset({"analyst_confirmed", "ofac_sdn", "sanctions"})
NEGATIVE_SOURCES = frozenset({"analyst_rejected"})


@dataclass
class EvalMetrics:
    precision: float
    recall: float
    f1: float
    support: int
    true_positives: int
    false_positives: int
    false_negatives: int
    engine_version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "support": self.support,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "engine_version": self.engine_version,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }


def _binary_metrics(y_true: list[int], y_pred: list[int]) -> EvalMetrics:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return EvalMetrics(
        precision=precision,
        recall=recall,
        f1=f1,
        support=len(y_true),
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
    )


async def load_analyst_labeled_rows() -> list[dict[str, Any]]:
    """Ground truth from compliance_entity_labels (analyst confirmed/rejected)."""
    rows: list[dict[str, Any]] = []
    try:
        from sqlalchemy import create_engine, text

        url = os.getenv("DATABASE_URL")
        if not url:
            return rows
        engine = create_engine(url)
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT chain, address, source, label, risk_score, confidence
                    FROM compliance_entity_labels
                    WHERE source IN ('analyst_confirmed', 'analyst_rejected')
                    """
                )
            )
            for r in result.mappings():
                rows.append(dict(r))
    except Exception:
        pass
    return rows


async def predict_risk_for_address(chain: str, address: str) -> int:
    """Run attribution engine; 1 = flagged high-risk, 0 = clear."""
    try:
        from flowsint_crypto_compliance.attribution import AttributionEngine
        from flowsint_crypto_compliance.demo.demo_context import get_demo_label_cache
        from flowsint_types.fiat_crypto import Chain

        engine = AttributionEngine(label_cache=get_demo_label_cache())
        ch = Chain(chain) if chain in Chain.__members__.values() else Chain.TRON
        result = await engine.attribute_wallet(address, ch)
        score = float(getattr(result, "risk_score", 0) or 0)
        sanctioned = bool(getattr(result, "sanctioned", False))
        return 1 if sanctioned or score >= 55 else 0
    except Exception:
        return 0


async def build_evaluation_dataset(max_rows: int = 500) -> tuple[list[int], list[int], list[dict]]:
    rows = await load_analyst_labeled_rows()
    y_true: list[int] = []
    y_pred: list[int] = []
    details: list[dict] = []
    for row in rows[:max_rows]:
        source = str(row.get("source") or "")
        if source in POSITIVE_SOURCES:
            label = 1
        elif source in NEGATIVE_SOURCES:
            label = 0
        else:
            continue
        pred = await predict_risk_for_address(str(row["chain"]), str(row["address"]))
        y_true.append(label)
        y_pred.append(pred)
        details.append({**row, "predicted": pred, "ground_truth": label})
    return y_true, y_pred, details


async def run_attribution_evaluation(*, engine_version: str = "1.0") -> dict[str, Any]:
    y_true, y_pred, details = await build_evaluation_dataset()
    if not y_true:
        return {"status": "skipped", "reason": "no_analyst_labeled_rows", "metrics": None}

    metrics = _binary_metrics(y_true, y_pred)
    metrics.engine_version = engine_version
    payload = {"status": "ok", "metrics": metrics.to_dict(), "sample_size": len(y_true)}

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"eval_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    report_path.write_text(json.dumps({**payload, "details": details[:50]}, indent=2, ensure_ascii=False), encoding="utf-8")
    payload["report_path"] = str(report_path)

    drift_report = _evidently_drift_report(y_true, y_pred)
    if drift_report:
        payload["evidently"] = drift_report

    baseline = load_baseline()
    if baseline:
        payload["baseline_comparison"] = compare_to_baseline(metrics, baseline)
        payload["deploy_gate"] = deploy_gate(metrics, baseline)
    else:
        save_baseline(metrics)
        payload["baseline_saved"] = True

    return payload


def load_baseline() -> dict[str, Any] | None:
    if not BASELINE_FILE.is_file():
        return None
    return json.loads(BASELINE_FILE.read_text(encoding="utf-8"))


def save_baseline(metrics: EvalMetrics) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    BASELINE_FILE.write_text(json.dumps(metrics.to_dict(), indent=2), encoding="utf-8")


def compare_to_baseline(current: EvalMetrics, baseline: dict[str, Any]) -> dict[str, Any]:
    return {
        "precision_delta": round(current.precision - float(baseline.get("precision", 0)), 4),
        "recall_delta": round(current.recall - float(baseline.get("recall", 0)), 4),
        "f1_delta": round(current.f1 - float(baseline.get("f1", 0)), 4),
    }


def deploy_gate(
    current: EvalMetrics,
    baseline: dict[str, Any],
    *,
    min_precision: float | None = None,
    min_recall: float | None = None,
) -> dict[str, Any]:
    mp = float(os.getenv("FINSKALP_EVAL_MIN_PRECISION", min_precision or baseline.get("precision", 0.7)))
    mr = float(os.getenv("FINSKALP_EVAL_MIN_RECALL", min_recall or baseline.get("recall", 0.6)))
    passed = current.precision >= mp and current.recall >= mr
    return {
        "passed": passed,
        "min_precision": mp,
        "min_recall": mr,
        "action": "proceed" if passed else "block_rollout_review_required",
    }


def _evidently_drift_report(y_true: list[int], y_pred: list[int]) -> dict[str, Any] | None:
    try:
        import pandas as pd
        from evidently import Report
        from evidently.metrics import ClassificationQualityMetric

        df = pd.DataFrame({"target": y_true, "prediction": y_pred})
        report = Report(metrics=[ClassificationQualityMetric()])
        report.run(reference_data=df, current_data=df)
        return json.loads(report.json())
    except ImportError:
        return {"status": "evidently_not_installed", "install": "pip install evidently"}
    except Exception as exc:
        return {"status": "error", "detail": exc.__class__.__name__}
