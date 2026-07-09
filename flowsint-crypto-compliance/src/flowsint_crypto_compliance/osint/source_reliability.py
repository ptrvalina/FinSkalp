"""
Admiralty Code–inspired OSINT source reliability.

Historical precision from analyst confirmations and attribution eval;
integrated into Bayesian fusion as a multiplier on raw_confidence.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine, text

MIN_SAMPLE_FOR_ESTIMATE = int(os.getenv("FINSKALP_OSINT_RELIABILITY_MIN_SAMPLE", "5"))

# Default priors when DB row missing (source_type → precision)
_DEFAULT_PRIORS: dict[str, float] = {
    "explorer_tag": 0.88,
    "sanctions": 0.95,
    "otc_board": 0.85,
    "abuse_registry": 0.82,
    "vasp_registry": 0.86,
    "darknet_index": 0.58,
    "telegram": 0.70,
    "forum": 0.55,
    "web": 0.68,
    "paste": 0.40,
    "leak": 0.35,
    "username_social": 0.62,
    "username": 0.62,
    "clearnet_dork": 0.65,
    "prior_case_match": 0.90,
}

_inmem_cache: dict[str, dict[str, Any]] = {}


@dataclass
class SourceReliabilityRow:
    source_name: str
    historical_precision: float
    sample_size: int
    last_updated: str
    insufficient_data: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "historical_precision": round(self.historical_precision, 4),
            "sample_size": self.sample_size,
            "last_updated": self.last_updated,
            "insufficient_data": self.insufficient_data,
            "insufficient_data_ru": (
                "Недостаточно данных для оценки надёжности"
                if self.insufficient_data
                else None
            ),
        }


def default_reliability_for_source(
    source_type: str,
    reliability_map: dict[str, float] | None = None,
) -> float:
    if reliability_map:
        for key in (source_type, source_type.lower()):
            if key in reliability_map:
                return float(reliability_map[key])
    return _DEFAULT_PRIORS.get(source_type, _DEFAULT_PRIORS.get(source_type.lower(), 0.55))


def apply_source_reliability(
    source_name: str,
    fallback: float,
    *,
    reliability_map: dict[str, float] | None = None,
) -> float:
    if reliability_map and source_name in reliability_map:
        return float(reliability_map[source_name])
    row = lookup_source_reliability(source_name)
    if row and not row.insufficient_data:
        return row.historical_precision
    if row and row.insufficient_data:
        # Shrink toward neutral when sample too small
        return 0.5 + (row.historical_precision - 0.5) * 0.35
    st = source_name.split(":")[0] if ":" in source_name else source_name
    return default_reliability_for_source(st, reliability_map)


def lookup_source_reliability(source_name: str) -> SourceReliabilityRow | None:
    key = source_name.strip().lower()
    if key in _inmem_cache:
        c = _inmem_cache[key]
        return SourceReliabilityRow(**c)

    url = os.getenv("DATABASE_URL")
    if not url:
        return None
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT source_name, historical_precision, sample_size, last_updated
                    FROM osint_source_reliability
                    WHERE lower(source_name) = lower(:name)
                    LIMIT 1
                    """
                ),
                {"name": source_name},
            ).mappings().first()
            if not row:
                return None
            sample = int(row["sample_size"] or 0)
            return SourceReliabilityRow(
                source_name=str(row["source_name"]),
                historical_precision=float(row["historical_precision"] or 0.5),
                sample_size=sample,
                last_updated=str(row["last_updated"] or ""),
                insufficient_data=sample < MIN_SAMPLE_FOR_ESTIMATE,
            )
    except Exception:
        return None


def load_reliability_map() -> dict[str, float]:
    """Bulk load for fusion — source_name → precision."""
    out: dict[str, float] = dict(_DEFAULT_PRIORS)
    out.update({k: float(v["historical_precision"]) for k, v in _inmem_cache.items()})

    url = os.getenv("DATABASE_URL")
    if not url:
        return out
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT source_name, historical_precision, sample_size
                    FROM osint_source_reliability
                    """
                )
            ).mappings()
            for r in rows:
                name = str(r["source_name"])
                sample = int(r["sample_size"] or 0)
                prec = float(r["historical_precision"] or 0.5)
                if sample < MIN_SAMPLE_FOR_ESTIMATE:
                    prec = 0.5 + (prec - 0.5) * 0.35
                out[name.lower()] = prec
    except Exception:
        pass
    return out


def record_analyst_feedback(
    *,
    source_name: str,
    confirmed: bool,
    osint_source_type: str | None = None,
) -> SourceReliabilityRow:
    """Update reliability from analyst confirm/reject (in-memory + Postgres)."""
    key = source_name.strip().lower()
    now = datetime.now(timezone.utc).isoformat()
    existing = _inmem_cache.get(key, {})
    sample = int(existing.get("sample_size") or 0)
    prec = float(existing.get("historical_precision") or default_reliability_for_source(osint_source_type or key))
    # Running precision: incremental mean of binary outcomes
    sample += 1
    outcome = 1.0 if confirmed else 0.0
    prec = prec + (outcome - prec) / sample
    row = SourceReliabilityRow(
        source_name=source_name,
        historical_precision=prec,
        sample_size=sample,
        last_updated=now,
        insufficient_data=sample < MIN_SAMPLE_FOR_ESTIMATE,
    )
    _inmem_cache[key] = {
        "source_name": row.source_name,
        "historical_precision": row.historical_precision,
        "sample_size": row.sample_size,
        "last_updated": row.last_updated,
        "insufficient_data": row.insufficient_data,
    }
    _persist_reliability_row(row)
    return row


def sync_from_attribution_eval() -> dict[str, Any]:
    """Bootstrap reliability rows from compliance_entity_labels analyst feedback."""
    url = os.getenv("DATABASE_URL")
    if not url:
        return {"status": "skipped", "reason": "no_database"}
    updated = 0
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT
                      COUNT(*) FILTER (WHERE source = 'analyst_confirmed') AS confirmed,
                      COUNT(*) FILTER (WHERE source = 'analyst_rejected') AS rejected
                    FROM compliance_entity_labels
                    WHERE source IN ('analyst_confirmed', 'analyst_rejected')
                    """
                )
            ).mappings().first()
            if rows:
                confirmed = int(rows["confirmed"] or 0)
                rejected = int(rows["rejected"] or 0)
                total = confirmed + rejected
                if total > 0:
                    prec = confirmed / total
                    name = "attribution:analyst_labels"
                    row = SourceReliabilityRow(
                        source_name=name,
                        historical_precision=prec,
                        sample_size=total,
                        last_updated=datetime.now(timezone.utc).isoformat(),
                        insufficient_data=total < MIN_SAMPLE_FOR_ESTIMATE,
                    )
                    _persist_reliability_row(row, conn=conn)
                    _inmem_cache[name.lower()] = {
                        "source_name": name,
                        "historical_precision": prec,
                        "sample_size": total,
                        "last_updated": row.last_updated,
                        "insufficient_data": row.insufficient_data,
                    }
                    updated += 1
        return {"status": "ok", "sources_updated": updated}
    except Exception as exc:
        return {"status": "error", "detail": exc.__class__.__name__}


def _persist_reliability_row(row: SourceReliabilityRow, *, conn: Any | None = None) -> None:
    url = os.getenv("DATABASE_URL")
    if not url:
        return
    sql = text(
        """
        INSERT INTO osint_source_reliability
            (source_name, historical_precision, sample_size, last_updated)
        VALUES (:name, :prec, :sample, :updated)
        ON CONFLICT (source_name) DO UPDATE SET
            historical_precision = EXCLUDED.historical_precision,
            sample_size = EXCLUDED.sample_size,
            last_updated = EXCLUDED.last_updated
        """
    )
    params = {
        "name": row.source_name,
        "prec": row.historical_precision,
        "sample": row.sample_size,
        "updated": row.last_updated,
    }
    try:
        if conn is not None:
            conn.execute(sql, params)
            conn.commit()
            return
        engine = create_engine(url)
        with engine.connect() as c:
            c.execute(sql, params)
            c.commit()
    except Exception:
        pass
