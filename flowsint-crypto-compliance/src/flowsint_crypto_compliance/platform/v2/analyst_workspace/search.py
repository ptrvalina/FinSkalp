"""RFC-0010 Ch.5 — Universal search across workspace data sources."""

from __future__ import annotations

import os
import uuid
from typing import Any

from flowsint_crypto_compliance.platform.v2 import knowledge_store as kg_store_mod
from flowsint_crypto_compliance.platform.v2.canonical import EntityType
from flowsint_crypto_compliance.platform.v2.investigation_platform import get_investigation_platform_service


def default_tenant_id() -> uuid.UUID:
    return uuid.UUID(os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001"))


def _entity_hit(ent: Any) -> dict[str, Any]:
    label = ent.display_name or ent.canonical_key
    is_case = ent.entity_type == EntityType.CASE
    case_ref = None
    if is_case:
        case_ref = ent.canonical_key.removeprefix("case:") if ent.canonical_key.startswith("case:") else ent.canonical_key
    return {
        "id": str(ent.id),
        "kind": "case" if is_case else "entity",
        "entity_type": ent.entity_type.value,
        "canonical_key": ent.canonical_key,
        "display_name": label,
        "case_ref": case_ref,
    }


def universal_search(
    query: str,
    tenant_id: uuid.UUID | None = None,
    *,
    case_ref: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Search cases, KG entities, and case evidence (memory / postgres backends)."""
    needle = (query or "").strip()
    if not needle:
        return {
            "ok": False,
            "message_ru": "Укажите поисковый запрос",
            "query": query,
            "results": [],
            "counts": {"cases": 0, "entities": 0, "evidence": 0, "total": 0},
        }

    tid = tenant_id or default_tenant_id()
    store = kg_store_mod.get_knowledge_graph_store()
    platform = get_investigation_platform_service()
    needle_lower = needle.lower()

    cases: list[dict[str, Any]] = []
    entities: list[dict[str, Any]] = []
    seen_entity_ids: set[str] = set()

    for ent in store.list_entities(tid):
        label = ent.display_name or ent.canonical_key
        if needle_lower not in ent.canonical_key.lower() and needle_lower not in (label or "").lower():
            continue
        item = _entity_hit(ent)
        seen_entity_ids.add(item["id"])
        if item["kind"] == "case":
            cases.append(item)
        else:
            entities.append(item)

    for ent in store.search_entities_by_value(tid, needle):
        eid = str(ent.id)
        if eid in seen_entity_ids:
            continue
        item = _entity_hit(ent)
        seen_entity_ids.add(eid)
        if item["kind"] == "case":
            cases.append(item)
        else:
            entities.append(item)

    evidence: list[dict[str, Any]] = []
    evidence_cases = [case_ref] if case_ref else [c.get("case_ref") or c.get("canonical_key") for c in cases]
    evidence_cases = [r for r in dict.fromkeys(evidence_cases) if r]

    if case_ref and case_ref not in evidence_cases:
        evidence_cases.insert(0, case_ref)

    for ref in evidence_cases:
        ev_data = platform.list_evidence(case_ref=ref, tenant_id=tid)
        for row in ev_data.get("items") or []:
            payload = row.get("payload") or {}
            hay = " ".join(
                [
                    str(row.get("id", "")),
                    str(row.get("source_type", "")),
                    str(row.get("content_hash", "")),
                    str(payload.get("entity_value", "")),
                    str(payload.get("entity_type", "")),
                ]
            ).lower()
            if needle_lower not in hay:
                continue
            evidence.append(
                {
                    "id": str(row.get("id")),
                    "kind": "evidence",
                    "source_type": row.get("source_type"),
                    "content_hash": row.get("content_hash"),
                    "case_ref": ref,
                    "status": row.get("status"),
                    "display_name": f"{row.get('source_type')} · {str(row.get('content_hash', ''))[:12]}",
                }
            )

    if case_ref:
        cases = [
            c
            for c in cases
            if c.get("case_ref") == case_ref
            or c.get("canonical_key") == case_ref
            or c.get("canonical_key") == f"case:{case_ref}"
        ]

    all_results = (cases + entities + evidence)[:limit]
    return {
        "ok": True,
        "query": needle,
        "case_ref": case_ref,
        "tenant_id": str(tid),
        "results": all_results,
        "counts": {
            "cases": len(cases),
            "entities": len(entities),
            "evidence": len(evidence),
            "total": len(all_results),
        },
    }
