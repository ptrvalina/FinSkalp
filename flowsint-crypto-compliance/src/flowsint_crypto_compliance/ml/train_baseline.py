"""
Train XGBoost baseline on Elliptic-style features and export ONNX.

Usage:
  uv run python -m flowsint_crypto_compliance.ml.train_baseline
  uv run python -m flowsint_crypto_compliance.ml.train_baseline --csv /path/to/elliptic.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from flowsint_crypto_compliance.ml.features import FEATURE_NAMES

_DEFAULT_OUT = Path(__file__).resolve().parents[1] / "data" / "models" / "risk_xgb.onnx"


def _synthetic_elliptic(n: int = 4000, *, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    """Synthetic licit/illicit distribution mirroring Elliptic feature statistics."""
    rng = np.random.default_rng(seed)
    X = rng.uniform(0, 1, size=(n, len(FEATURE_NAMES))).astype(np.float32)
    illicit_mask = (
        (X[:, 4] > 0.5)
        | (X[:, 5] > 0.6)
        | ((X[:, 0] > 0.4) & (X[:, 1] > 0.5))
    )
    y = illicit_mask.astype(np.int32)
    return X, y


def _load_elliptic_csv(path: Path) -> tuple[np.ndarray, np.ndarray]:
    import pandas as pd

    df = pd.read_csv(path)
    if "class" in df.columns:
        y = (df["class"] == "illicit").astype(np.int32).values
        X = df.drop(columns=["class"], errors="ignore").values.astype(np.float32)
        if X.shape[1] != len(FEATURE_NAMES):
            X = X[:, : len(FEATURE_NAMES)]
        return X, y
    raise ValueError("CSV must contain 'class' column (licit/illicit)")


def train_and_export(
    *,
    csv_path: Path | None = None,
    out_path: Path | None = None,
) -> Path:
    out = out_path or _DEFAULT_OUT
    out.parent.mkdir(parents=True, exist_ok=True)

    if csv_path and csv_path.is_file():
        X, y = _load_elliptic_csv(csv_path)
    else:
        X, y = _synthetic_elliptic()

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = XGBClassifier(
        n_estimators=80,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.9,
        eval_metric="logloss",
    )
    model.fit(X_train, y_train)
    acc = float(model.score(X_test, y_test))

    try:
        from onnxmltools import convert_xgboost
        from onnxmltools.convert.common.data_types import FloatTensorType

        onnx_model = convert_xgboost(
            model,
            initial_types=[("features", FloatTensorType([None, len(FEATURE_NAMES)]))],
            target_opset=12,
        )
        with out.open("wb") as f:
            f.write(onnx_model.SerializeToString())
    except ImportError as exc:
        raise RuntimeError("Install ml extras: uv sync --extra ml") from exc

    meta = out.with_suffix(".json")
    meta.write_text(
        f'{{"feature_names": {FEATURE_NAMES!r}, "test_accuracy": {acc:.4f}, "samples": {len(X)}}}',
        encoding="utf-8",
    )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Train FinSkalp risk XGBoost → ONNX")
    parser.add_argument("--csv", type=Path, default=None, help="Elliptic CSV (optional)")
    parser.add_argument("--out", type=Path, default=_DEFAULT_OUT)
    args = parser.parse_args()
    path = train_and_export(csv_path=args.csv, out_path=args.out)
    print(f"Exported ONNX model → {path}")


if __name__ == "__main__":
    main()
