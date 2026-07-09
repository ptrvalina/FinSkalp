from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from flowsint_types.fiat_crypto import Chain, RegistrySource, SovereignRiskLabel


def parse_registry_jsonl(path: Path) -> list[SovereignRiskLabel]:
    labels: list[SovereignRiskLabel] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            labels.append(parse_registry_row(json.loads(line)))
    return labels


def parse_registry_csv(path: Path) -> list[SovereignRiskLabel]:
    labels: list[SovereignRiskLabel] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            labels.append(parse_registry_row(row))
    return labels


def parse_registry_row(row: dict[str, Any]) -> SovereignRiskLabel:
    source = str(row.get("source") or row.get("provider") or "other").lower()
    return SovereignRiskLabel(
        label_id=str(
            row.get("label_id")
            or row.get("id")
            or f"{row['address']}-{source}"
        ),
        source=_to_source(source),
        chain=Chain(str(row["chain"]).lower()),
        address=str(row["address"]),
        entity_name=row.get("entity_name") or row.get("entity"),
        category=row.get("category"),
        risk_score=_float_or_none(row.get("risk_score")),
        confidence=float(row.get("confidence", 0.5)),
        sanctioned=_truthy(row.get("sanctioned")),
        list_reference=row.get("list_reference"),
        disputed=_truthy(row.get("disputed")),
        snapshot_at=row.get("snapshot_at"),
        cluster_ref=row.get("cluster_ref"),
    )


def _to_source(value: str) -> RegistrySource:
    try:
        return RegistrySource(value)
    except ValueError:
        return RegistrySource.OTHER


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in ("1", "true", "yes", "да")


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
