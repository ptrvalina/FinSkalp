"""Active learning — закрытые CASE_SAR/HOLISTIC → labeled samples."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_STORE = Path(__file__).resolve().parents[1] / "data" / "ml" / "active_labels.jsonl"


def append_case_label(
    *,
    case_ref: str,
    address: str,
    chain: str,
    label: str,
    risk_score: float,
    features: dict[str, float] | None = None,
    source: str = "CASE_SAR",
) -> dict[str, Any]:
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "case_ref": case_ref,
        "address": address,
        "chain": chain,
        "label": label,
        "risk_score": risk_score,
        "features": features or {},
        "source": source,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    with _STORE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def load_active_labels(limit: int = 10_000) -> list[dict[str, Any]]:
    if not _STORE.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in _STORE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows[-limit:]


def active_label_count() -> int:
    return len(load_active_labels())
