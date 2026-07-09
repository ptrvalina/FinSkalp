"""
Institutional memory — cross-reference OSINT entities against closed cases (tenant-scoped).
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine, text

CLOSED_WORKFLOW_STATUSES = frozenset({"filed", "archived"})

FINDING_ENTITY_TYPES = frozenset({"domain", "username", "onion", "phone", "email", "crypto_address"})


@dataclass
class PriorCaseMatch:
    entity_type: str
    entity_value: str
    prior_case_ref: str
    prior_case_id: str
    closed_status: str
    match_strength: float
    title_ru: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "entity_value": self.entity_value,
            "prior_case_ref": self.prior_case_ref,
            "prior_case_id": self.prior_case_id,
            "closed_status": self.closed_status,
            "match_strength": round(self.match_strength, 3),
            "priority_flag": "PRIOR_CASE_MATCH",
            "title_ru": self.title_ru,
            "link_ru": f"Дело {self.prior_case_ref} ({self.closed_status})",
        }


@dataclass
class InstitutionalMemoryResult:
    matches: list[PriorCaseMatch] = field(default_factory=list)
    checked_entities: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "matches": [m.to_dict() for m in self.matches],
            "checked_entities": self.checked_entities,
            "has_prior_case_match": bool(self.matches),
        }

    @property
    def has_prior_case_match(self) -> bool:
        return bool(self.matches)


_inmem_findings: list[dict[str, Any]] = []


def normalize_entity(entity_type: str, value: str) -> tuple[str, str]:
    et = entity_type.strip().lower()
    v = value.strip()
    if et == "username":
        v = v.lstrip("@").lower()
    elif et in ("domain", "onion"):
        v = v.lower().removeprefix("http://").removeprefix("https://").split("/")[0]
    elif et == "email":
        v = v.lower()
    elif et == "phone":
        v = "".join(c for c in v if c.isdigit())[-10:]
    return et, v


def extract_entities_from_osint(extracted: dict[str, Any], mentions: list[dict[str, Any]] | None = None) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    agg = extracted.get("aggregate") or extracted
    for d in agg.get("domains") or []:
        out.append(("domain", str(d)))
    for u in agg.get("usernames") or []:
        out.append(("username", str(u)))
    for p in agg.get("phones") or []:
        out.append(("phone", str(p)))
    for e in agg.get("emails") or []:
        out.append(("email", str(e)))
    for item in agg.get("crypto_addresses") or []:
        addr = item.get("address") if isinstance(item, dict) else str(item)
        if addr:
            out.append(("crypto_address", str(addr)))
    for m in mentions or []:
        url = (m.get("url") or "") if isinstance(m, dict) else ""
        if ".onion" in url.lower():
            host = url.lower().split("//")[-1].split("/")[0]
            out.append(("onion", host))
    seen: set[tuple[str, str]] = set()
    deduped: list[tuple[str, str]] = []
    for et, v in out:
        key = normalize_entity(et, v)
        if key[1] and key not in seen:
            seen.add(key)
            deduped.append(key)
    return deduped


def cross_reference_closed_cases(
    *,
    tenant_id: str | uuid.UUID,
    entities: list[tuple[str, str]],
    exclude_case_ref: str | None = None,
) -> InstitutionalMemoryResult:
    """Search osint_findings + closed compliance_cases for entity overlap."""
    if not entities:
        return InstitutionalMemoryResult()

    tenant = str(tenant_id)
    matches: list[PriorCaseMatch] = []
    checked = len(entities)

    db_matches = _query_postgres(tenant, entities, exclude_case_ref)
    mem_matches = _query_inmem(tenant, entities, exclude_case_ref)
    seen_refs: set[str] = set()
    for m in db_matches + mem_matches:
        key = f"{m.prior_case_ref}:{m.entity_type}:{m.entity_value}"
        if key not in seen_refs:
            seen_refs.add(key)
            matches.append(m)

    matches.sort(key=lambda x: -x.match_strength)
    return InstitutionalMemoryResult(matches=matches, checked_entities=checked)


def persist_osint_finding(
    *,
    tenant_id: str | uuid.UUID,
    case_id: str | uuid.UUID,
    case_ref: str,
    entity_type: str,
    entity_value: str,
    source_type: str,
    confidence: float,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Store finding for future institutional memory lookups."""
    et, ev = normalize_entity(entity_type, entity_value)
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "id": str(uuid.uuid4()),
        "tenant_id": str(tenant_id),
        "case_id": str(case_id),
        "case_ref": case_ref,
        "entity_type": et,
        "entity_value": ev,
        "source_type": source_type,
        "confidence": confidence,
        "payload": payload or {},
        "discovered_at": now,
    }
    _inmem_findings.append(row)
    _persist_finding_postgres(row)
    try:
        from flowsint_crypto_compliance.platform.v2.evidence_center import dual_write_osint_finding

        dual_write_osint_finding(row)
    except Exception:
        pass
    return row


def index_findings_from_scalpel(
    *,
    tenant_id: str | uuid.UUID,
    case_id: str | uuid.UUID,
    case_ref: str,
    extracted_entities: dict[str, Any],
    mentions: list[dict[str, Any]],
) -> int:
    count = 0
    entities = extract_entities_from_osint(extracted_entities, mentions)
    for et, ev in entities:
        conf = 0.6
        for m in mentions:
            if isinstance(m, dict):
                conf = max(conf, float(m.get("confidence") or 0.5))
        persist_osint_finding(
            tenant_id=tenant_id,
            case_id=case_id,
            case_ref=case_ref,
            entity_type=et,
            entity_value=ev,
            source_type="scalpel_extract",
            confidence=conf,
        )
        count += 1
    return count


def _query_inmem(
    tenant_id: str,
    entities: list[tuple[str, str]],
    exclude_case_ref: str | None,
) -> list[PriorCaseMatch]:
    out: list[PriorCaseMatch] = []
    norm_entities = {normalize_entity(et, v) for et, v in entities}
    for f in _inmem_findings:
        if f.get("tenant_id") != tenant_id:
            continue
        if exclude_case_ref and f.get("case_ref") == exclude_case_ref:
            continue
        key = (f.get("entity_type"), f.get("entity_value"))
        if key not in norm_entities:
            continue
        out.append(
            PriorCaseMatch(
                entity_type=str(f["entity_type"]),
                entity_value=str(f["entity_value"]),
                prior_case_ref=str(f.get("case_ref") or ""),
                prior_case_id=str(f.get("case_id") or ""),
                closed_status="archived",
                match_strength=float(f.get("confidence") or 0.7),
                title_ru=f"Совпадение с закрытым делом · {f.get('entity_type')}",
            )
        )
    return out


def _query_postgres(
    tenant_id: str,
    entities: list[tuple[str, str]],
    exclude_case_ref: str | None,
) -> list[PriorCaseMatch]:
    url = os.getenv("DATABASE_URL")
    if not url or not entities:
        return []
    out: list[PriorCaseMatch] = []
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            for et, ev in entities:
                et_n, ev_n = normalize_entity(et, ev)
                rows = conn.execute(
                    text(
                        """
                        SELECT f.entity_type, f.entity_value, f.confidence,
                               f.case_ref, f.case_id::text AS case_id,
                               c.workflow_status
                        FROM osint_findings f
                        JOIN compliance_cases c ON c.id = f.case_id
                        WHERE f.tenant_id = :tenant
                          AND f.entity_type = :etype
                          AND f.entity_value = :evalue
                          AND c.workflow_status IN ('filed', 'archived')
                          AND (:exclude IS NULL OR f.case_ref <> :exclude)
                        ORDER BY f.discovered_at DESC
                        LIMIT 5
                        """
                    ),
                    {
                        "tenant": tenant_id,
                        "etype": et_n,
                        "evalue": ev_n,
                        "exclude": exclude_case_ref,
                    },
                ).mappings()
                for r in rows:
                    out.append(
                        PriorCaseMatch(
                            entity_type=str(r["entity_type"]),
                            entity_value=str(r["entity_value"]),
                            prior_case_ref=str(r["case_ref"]),
                            prior_case_id=str(r["case_id"]),
                            closed_status=str(r["workflow_status"]),
                            match_strength=float(r["confidence"] or 0.75),
                            title_ru=(
                                f"PRIOR CASE MATCH: {et_n} «{ev_n[:32]}» "
                                f"в деле {r['case_ref']}"
                            ),
                        )
                    )
    except Exception:
        pass
    return out


def _persist_finding_postgres(row: dict[str, Any]) -> None:
    url = os.getenv("DATABASE_URL")
    if not url:
        return
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO osint_findings
                        (id, tenant_id, case_id, case_ref, entity_type, entity_value,
                         source_type, confidence, payload, discovered_at)
                    VALUES
                        (:id::uuid, :tenant::uuid, :case_id::uuid, :case_ref,
                         :entity_type, :entity_value, :source_type, :confidence,
                         :payload::jsonb, :discovered_at::timestamptz)
                    ON CONFLICT (tenant_id, entity_type, entity_value, case_id) DO NOTHING
                    """
                ),
                {
                    **row,
                    "payload": __import__("json").dumps(row.get("payload") or {}),
                },
            )
            conn.commit()
    except Exception:
        pass
