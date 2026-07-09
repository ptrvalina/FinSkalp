from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable

from flowsint_crypto_compliance.ingestion.sovereign_registry import parse_registry_row
from flowsint_types.fiat_crypto import SovereignRiskLabel


def stage_registry_jsonl(path: Path) -> list[SovereignRiskLabel]:
    """
    Load a sovereign registry JSONL snapshot through DuckDB for deduplication.

    Keeps the highest-confidence row per (chain, address); sanctioned rows win ties.
    """
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return _dedupe_rows(rows)


def stage_registry_lines(lines: Iterable[str]) -> list[SovereignRiskLabel]:
    """Deduplicate in-memory JSONL lines before PostgreSQL upsert."""
    rows: list[dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return _dedupe_rows(rows)


def stage_registry_parquet(path: Path) -> list[SovereignRiskLabel]:
    """Load deduplicated labels from Parquet snapshot (DuckDB)."""
    import duckdb

    conn = duckdb.connect(":memory:")
    deduped = conn.execute(
        f"""
        SELECT *
        FROM read_parquet('{_duck_path(path)}')
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY chain, address
            ORDER BY
                COALESCE(sanctioned, FALSE) DESC,
                COALESCE(confidence, 0.5) DESC
        ) = 1
        """
    ).fetchdf()
    conn.close()
    return [parse_registry_row(_stringify_keys(record)) for record in deduped.to_dict(orient="records")]


def export_registry_parquet(labels: list[SovereignRiskLabel], path: Path) -> Path:
    """Persist deduplicated labels to Parquet for air-gap handoff."""
    import duckdb

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [label.model_dump(mode="json") for label in labels]
    with _temp_jsonl(payload) as jsonl_path:
        conn = duckdb.connect(":memory:")
        conn.execute(
            f"""
            COPY (
                SELECT * FROM read_json_auto('{_duck_path(jsonl_path)}')
            ) TO '{_duck_path(path)}' (FORMAT PARQUET)
            """
        )
        conn.close()
    return path


def _dedupe_rows(rows: list[dict[str, Any]]) -> list[SovereignRiskLabel]:
    if not rows:
        return []

    import duckdb

    normalized = [
        {
            **row,
            "sanctioned": bool(row.get("sanctioned", False)),
            "confidence": float(row.get("confidence", 0.5)),
        }
        for row in rows
    ]

    with _temp_jsonl(normalized) as jsonl_path:
        conn = duckdb.connect(":memory:")
        deduped = conn.execute(
            f"""
            SELECT *
            FROM read_json_auto('{_duck_path(jsonl_path)}')
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY chain, address
                ORDER BY
                    COALESCE(sanctioned, FALSE) DESC,
                    COALESCE(confidence, 0.5) DESC
            ) = 1
            """
        ).fetchdf()
        conn.close()

    return [parse_registry_row(_stringify_keys(record)) for record in deduped.to_dict(orient="records")]


def _temp_jsonl(rows: list[dict[str, Any]]):
    class _TempJsonl:
        def __enter__(self) -> Path:
            handle = tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".jsonl",
                encoding="utf-8",
                delete=False,
            )
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            handle.close()
            self._path = Path(handle.name)
            return self._path

        def __exit__(self, *_: object) -> None:
            if hasattr(self, "_path"):
                os.unlink(self._path)

    return _TempJsonl()


def _duck_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def _stringify_keys(record: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in record.items():
        if value is None or (isinstance(value, float) and value != value):
            continue
        cleaned[str(key)] = value
    return cleaned
