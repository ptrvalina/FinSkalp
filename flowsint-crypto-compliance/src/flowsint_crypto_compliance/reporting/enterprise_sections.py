"""Optional enterprise report sections (additive, backward-compatible).

This module derives *presentation-only* enterprise sections from data that is
**already present** in a built report dict. It:

* introduces **no new API** and calls no external service;
* **duplicates no data** — it reads existing report keys and reshapes them;
* writes a single namespaced key ``report["enterprise_sections"]`` so it can
  never overwrite or collide with existing top-level fields;
* is guarded by the ``enterprise_report_sections`` feature flag at the call
  site and is fully defensive here (a failing sub-section is skipped, never
  raised), so it cannot break legacy report generation.

Rollback: unset ``FINSKALP_ENTERPRISE_REPORT_SECTIONS`` — the ``enterprise_sections``
key is simply not produced and every template's ``{% if %}`` block is skipped.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)

_SCHEMA_VERSION = "enterprise-sections/v1"


def enrich_enterprise_sections(
    report: dict[str, Any], *, context: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Attach ``report['enterprise_sections']`` derived from existing data.

    Returns the same ``report`` object (mutated in place, like the existing
    ``enrich_forensic_report``). If ``enterprise_sections`` already exists it is
    preserved and merged under (never overwritten).
    """
    context = context or {}
    builders: list[tuple[str, Callable[[dict[str, Any], dict[str, Any]], Any]]] = [
        ("executive_summary", _executive_summary),
        ("risk_matrix", _risk_matrix),
        ("confidence_matrix", _confidence_matrix),
        ("evidence_quality", _evidence_quality),
        ("evidence_timeline", _evidence_timeline),
        ("graph_legend", _graph_legend),
        ("graph_statistics", _graph_statistics),
        ("investigation_metrics", _investigation_metrics),
        ("ai_summary", _ai_summary),
        ("explainability", _explainability),
        ("case_metadata", _case_metadata),
        ("digital_signature_placeholder", _digital_signature_placeholder),
        ("audit_metadata", _audit_metadata),
        ("report_versions", _report_versions),
        ("chain_of_custody", _chain_of_custody),
        ("rde_priorities", _rde_priorities),
        ("eccf_integrity", _eccf_integrity),
    ]

    sections: dict[str, Any] = {}
    for name, fn in builders:
        try:
            value = fn(report, context)
        except Exception:  # never let one section break report generation
            logger.exception("enterprise_sections: builder %s failed", name)
            continue
        if value:
            sections[name] = value

    if not sections:
        return report

    existing = report.get("enterprise_sections")
    if isinstance(existing, dict):
        # Preserve anything a builder already set; only fill gaps.
        for key, value in sections.items():
            existing.setdefault(key, value)
        existing.setdefault("_schema", _SCHEMA_VERSION)
    else:
        sections["_schema"] = _SCHEMA_VERSION
        report["enterprise_sections"] = sections
    return report


# --- helpers ------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _onchain(report: dict[str, Any]) -> dict[str, Any]:
    return report.get("onchain") or report.get("onchain_summary") or {}


def _level_from_score(score: float) -> str:
    if score >= 75:
        return "critical"
    if score >= 55:
        return "high"
    if score >= 35:
        return "moderate"
    return "low"


# --- section builders ---------------------------------------------------------


def _executive_summary(report: dict[str, Any], _ctx: dict[str, Any]) -> dict[str, Any] | None:
    exec_sum = report.get("executive_summary") or {}
    text = exec_sum.get("text_ru") or report.get("audit_result_ru") or report.get("summary_ru")
    highlights = list(exec_sum.get("key_findings_ru") or [])
    if not text and not highlights:
        return None
    return {
        "heading_ru": "Управляющее резюме",
        "text_ru": text or "—",
        "highlights_ru": highlights[:8],
        "recommended_actions_ru": list(exec_sum.get("recommended_actions_ru") or [])[:8],
    }


def _risk_matrix(report: dict[str, Any], _ctx: dict[str, Any]) -> dict[str, Any] | None:
    rows: list[dict[str, Any]] = []
    breakdown = report.get("risk_score_breakdown") or {}
    for comp in breakdown.get("components") or []:
        pts = float(comp.get("points") or 0)
        rows.append(
            {
                "dimension": comp.get("component"),
                "score": pts,
                "weight_pct": comp.get("pct"),
                "level": _level_from_score(pts * 2),
                "basis_ru": comp.get("explanation_ru"),
            }
        )
    if not rows:
        # Fall back to composite dimensions (address / forensic dict form).
        ra = report.get("risk_assessment")
        dims = {}
        if isinstance(ra, dict):
            dims = ra.get("dimensions") or {}
        for name, value in dims.items():
            try:
                score = float(value)
            except (TypeError, ValueError):
                continue
            rows.append(
                {
                    "dimension": name.replace("_", " ").title(),
                    "score": round(score, 1),
                    "weight_pct": None,
                    "level": _level_from_score(score),
                    "basis_ru": None,
                }
            )
    overall = report.get("risk_score")
    if overall is None and isinstance(report.get("risk_assessment"), dict):
        overall = report["risk_assessment"].get("composite_score")
    if not rows and overall is None:
        return None
    return {
        "heading_ru": "Матрица риска",
        "overall_score": overall,
        "overall_level": _level_from_score(float(overall)) if overall is not None else None,
        "rows": rows,
    }


def _confidence_matrix(report: dict[str, Any], _ctx: dict[str, Any]) -> dict[str, Any] | None:
    rows: list[dict[str, Any]] = []
    conf = report.get("overall_attribution_confidence") or {}
    if conf:
        rows.append(
            {
                "aspect_ru": "Атрибуция (совокупно)",
                "confidence_pct": conf.get("pct"),
                "label_ru": conf.get("label_ru") or conf.get("label"),
                "basis_ru": "; ".join(conf.get("factors_ru") or [])[:400] or None,
            }
        )
    source_status = report.get("source_status") or {}
    if isinstance(report.get("sanctions_check"), dict):
        source_status = {**source_status, **(report["sanctions_check"].get("source_status") or {})}
    ok = sum(1 for v in source_status.values() if str(v).lower() in ("ok", "available", "live"))
    if source_status:
        rows.append(
            {
                "aspect_ru": "Доступность источников",
                "confidence_pct": round(100 * ok / max(1, len(source_status)), 1),
                "label_ru": f"{ok}/{len(source_status)} источников доступно",
                "basis_ru": ", ".join(sorted(source_status)[:8]) or None,
            }
        )
    if not rows:
        return None
    return {"heading_ru": "Матрица достоверности", "rows": rows}


def _evidence_items(report: dict[str, Any]) -> list[Any]:
    return (
        report.get("evidence_inventory")
        or report.get("evidence_log")
        or report.get("evidence_chain")
        or []
    )


def _evidence_quality(report: dict[str, Any], _ctx: dict[str, Any]) -> dict[str, Any] | None:
    items = _evidence_items(report)
    if not items:
        return None
    total = len(items)
    hashed = 0
    tiers: dict[str, int] = {"tier_1": 0, "tier_2": 0, "tier_3": 0, "unknown": 0}
    for it in items:
        if isinstance(it, dict):
            if it.get("sha256") or it.get("hash"):
                hashed += 1
            tier = str(it.get("tier") or "").lower()
            if "1" in tier:
                tiers["tier_1"] += 1
            elif "2" in tier:
                tiers["tier_2"] += 1
            elif "3" in tier:
                tiers["tier_3"] += 1
            else:
                tiers["unknown"] += 1
        else:
            tiers["unknown"] += 1
    return {
        "heading_ru": "Качество доказательной базы",
        "total_exhibits": total,
        "hashed_pct": round(100 * hashed / total, 1),
        "tiers": tiers,
        "note_ru": "Оценка полноты и верификации зафиксированных доказательств.",
    }


def _evidence_timeline(report: dict[str, Any], _ctx: dict[str, Any]) -> dict[str, Any] | None:
    steps = report.get("activity_timeline")
    if not steps:
        onchain = _onchain(report)
        first = onchain.get("first_activity")
        last = onchain.get("last_activity") or report.get("generated_at")
        derived = []
        if first:
            derived.append({"ts": first, "label_ru": "Первая наблюдаемая активность"})
        if last:
            derived.append({"ts": last, "label_ru": "Последняя наблюдаемая активность / момент отчёта"})
        steps = derived or None
    if not steps:
        return None
    return {"heading_ru": "Хронология доказательств", "steps": steps}


def _graph_legend(report: dict[str, Any], _ctx: dict[str, Any]) -> dict[str, Any] | None:
    gs = report.get("graph_section") or {}
    fusion = report.get("fusion_report") or {}
    has_graph = bool(gs) or bool(fusion.get("evidence_graph"))
    if not has_graph:
        return None
    return {
        "heading_ru": "Легенда графа",
        "nodes": [
            {"color": "#dc2626", "meaning_ru": "Субъект / высокий риск"},
            {"color": "#f59e0b", "meaning_ru": "Серая зона / умеренный риск"},
            {"color": "#10b981", "meaning_ru": "Низкий риск / известная сущность"},
            {"color": "#6366f1", "meaning_ru": "Приоритетное направление трассировки"},
        ],
        "edges": [
            {"style": "сплошная", "meaning_ru": "Прямой перевод (ledger-confirmed)"},
            {"style": "пунктир", "meaning_ru": "Косвенная связь / эвристика"},
        ],
    }


def _graph_statistics(report: dict[str, Any], _ctx: dict[str, Any]) -> dict[str, Any] | None:
    gs = report.get("graph_section") or {}
    fusion = report.get("fusion_report") or {}
    eg = fusion.get("evidence_graph") or {}
    nodes = gs.get("node_count") or eg.get("nodes")
    edges = gs.get("edge_count") or eg.get("edges")
    fv = report.get("flow_visualization") or {}
    if nodes is None and edges is None and not fv.get("fusion_node_count"):
        return None
    nodes = nodes or fv.get("fusion_node_count") or 0
    edges = edges or fv.get("fusion_edge_count") or 0
    density = None
    if nodes and nodes > 1:
        density = round(edges / (nodes * (nodes - 1)), 4)
    return {
        "heading_ru": "Статистика графа",
        "nodes": nodes,
        "edges": edges,
        "density": density,
        "avg_degree": round(2 * edges / nodes, 2) if nodes else None,
    }


def _investigation_metrics(report: dict[str, Any], _ctx: dict[str, Any]) -> dict[str, Any] | None:
    onchain = _onchain(report)
    ap = report.get("address_profile") or {}
    metrics = {
        "inbound_tx": onchain.get("inbound_count") or ap.get("inbound_count"),
        "outbound_tx": onchain.get("outbound_count") or ap.get("outbound_count"),
        "counterparties": onchain.get("counterparties") or ap.get("counterparties") or report.get("connections_count"),
        "findings": len(report.get("findings") or []),
        "counterparty_records": len(report.get("counterparty_distribution") or report.get("counterparties") or []),
        "corridors": len(report.get("corridors") or []),
        "sanctions_hits": len((report.get("sanctions_check") or {}).get("hits") or report.get("sanctioned_hits") or []),
    }
    metrics = {k: v for k, v in metrics.items() if v}
    if not metrics:
        return None
    return {"heading_ru": "Статистика расследования", "metrics": metrics}


def _ai_summary(report: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any] | None:
    # Uses EIA output if the caller already attached it; never calls an LLM here.
    ai = report.get("ai_summary") or ctx.get("ai_summary")
    if isinstance(ai, dict) and ai.get("text_ru"):
        return {
            "heading_ru": "AI-резюме",
            "text_ru": ai["text_ru"],
            "generated_by": ai.get("generated_by") or "EIA",
            "disclaimer_ru": "Сгенерировано ассистентом расследования; требует проверки аналитиком.",
        }
    exec_sum = report.get("executive_summary") or {}
    text = exec_sum.get("text_ru")
    if not text:
        return None
    return {
        "heading_ru": "AI-резюме",
        "text_ru": text,
        "generated_by": "deterministic-fallback",
        "disclaimer_ru": "Детерминированное резюме на основе данных отчёта; LLM не задействован.",
    }


def _explainability(report: dict[str, Any], _ctx: dict[str, Any]) -> dict[str, Any] | None:
    breakdown = report.get("risk_score_breakdown") or {}
    comps = breakdown.get("components") or []
    if not comps:
        return None
    factors = [
        {
            "factor": c.get("component"),
            "contribution_pct": c.get("pct"),
            "points": c.get("points"),
            "explanation_ru": c.get("explanation_ru"),
        }
        for c in comps
        if (c.get("points") or 0) > 0
    ]
    if not factors:
        return None
    return {
        "heading_ru": "Объяснимость оценки",
        "methodology_ru": breakdown.get("methodology_ru"),
        "factors": sorted(factors, key=lambda f: f.get("contribution_pct") or 0, reverse=True),
    }


def _case_metadata(report: dict[str, Any], _ctx: dict[str, Any]) -> dict[str, Any] | None:
    ap = report.get("address_profile") or {}
    meta = {
        "case_ref": report.get("case_ref"),
        "report_id": report.get("report_id"),
        "report_type": report.get("report_type"),
        "product": report.get("product_ru") or report.get("product"),
        "version": report.get("version"),
        "classification": report.get("classification"),
        "generated_at": report.get("generated_at"),
        "address": report.get("address") or ap.get("address") or report.get("source_address"),
        "chain": report.get("chain") or report.get("network") or ap.get("network"),
    }
    meta = {k: v for k, v in meta.items() if v}
    if not meta.get("case_ref") and not meta.get("report_id"):
        return None
    return {"heading_ru": "Метаданные дела", **meta}


def _digital_signature_placeholder(report: dict[str, Any], _ctx: dict[str, Any]) -> dict[str, Any] | None:
    sig = report.get("digital_signature")
    if isinstance(sig, dict) and (sig.get("report_sha256") or sig.get("signature_value")):
        return {
            "heading_ru": "Цифровая подпись",
            "algorithm": sig.get("signature_algorithm") or "—",
            "report_sha256": sig.get("report_sha256"),
            "evidence_bundle_sha256": sig.get("evidence_bundle_sha256"),
            "signature_value": sig.get("signature_value"),
            "note_ru": sig.get("signature_note") or "Подпись формируется движком отчётов.",
            "status": "signed" if sig.get("signature_value") else "hash-only",
        }
    return {
        "heading_ru": "Цифровая подпись",
        "algorithm": None,
        "status": "placeholder",
        "note_ru": "Место для квалифицированной подписи (КЭП/HSM) при промышленном развёртывании.",
    }


def _audit_metadata(report: dict[str, Any], _ctx: dict[str, Any]) -> dict[str, Any] | None:
    sig = report.get("digital_signature") or {}
    db_versions = report.get("database_versions") or {}
    return {
        "heading_ru": "Аудит-метаданные",
        "generated_at": report.get("generated_at") or _now_iso(),
        "engine_version": report.get("version") or db_versions.get("engine_version"),
        "report_sha256": sig.get("report_sha256"),
        "generation_id": sig.get("generation_id"),
        "registry_snapshot": db_versions.get("registry_snapshot"),
        "sanctions_snapshot": db_versions.get("sanctions_snapshot"),
        "sections_flag": "enterprise_report_sections",
    }


def _report_versions(report: dict[str, Any], _ctx: dict[str, Any]) -> dict[str, Any] | None:
    return {
        "heading_ru": "Версии отчёта",
        "engine_version": report.get("version"),
        "schema_version": _SCHEMA_VERSION,
        "report_type": report.get("report_type"),
        "revision": report.get("revision") or 1,
        "history": report.get("report_history")
        or [{"revision": 1, "generated_at": report.get("generated_at"), "note_ru": "Первичная генерация"}],
    }


def _chain_of_custody(report: dict[str, Any], _ctx: dict[str, Any]) -> dict[str, Any] | None:
    items = _evidence_items(report)
    sig = report.get("digital_signature") or {}
    steps: list[dict[str, Any]] = []
    for i, it in enumerate(items[:20]):
        if isinstance(it, dict):
            steps.append(
                {
                    "seq": i + 1,
                    "exhibit_id": it.get("exhibit_id") or f"E{i + 1}",
                    "description_ru": it.get("description") or it.get("title_ru") or "Доказательство",
                    "sha256": it.get("sha256") or it.get("hash"),
                    "tier": it.get("tier"),
                }
            )
        else:
            steps.append({"seq": i + 1, "exhibit_id": f"E{i + 1}", "description_ru": str(it)[:80]})
    if not steps and not sig.get("evidence_bundle_sha256"):
        return None
    return {
        "heading_ru": "Цепочка сохранности (chain of custody)",
        "evidence_bundle_sha256": sig.get("evidence_bundle_sha256"),
        "custodian_ru": report.get("product_ru") or "ФинСкальп",
        "steps": steps,
        "note_ru": "Представление зафиксированной цепочки доказательств; неизменяемое хранение — ECCF.",
    }


def _rde_priorities(report: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any] | None:
    case_ref = report.get("case_ref") or ctx.get("case_ref")
    if not case_ref:
        return None
    try:
        from flowsint_crypto_compliance.platform.v2.gateway import get_rde_priorities as _get_rde_priorities

        data = _get_rde_priorities(case_ref)
        priorities = data.get("priorities") or data.get("items") or []
        if not priorities and not data.get("case_ref"):
            return None
        return {
            "heading_ru": "RDE — приоритеты расследования",
            "case_ref": case_ref,
            "priorities": priorities[:10],
            "monitoring": data.get("monitoring"),
        }
    except Exception:
        logger.debug("enterprise_sections: RDE priorities skipped", exc_info=True)
        return None


def _eccf_integrity(report: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any] | None:
    evidence_ids: list[str] = list(ctx.get("evidence_ids") or [])
    for item in _evidence_items(report):
        if isinstance(item, dict):
            eid = item.get("evidence_id") or item.get("eccf_id")
            if eid:
                evidence_ids.append(str(eid))
    evidence_ids = list(dict.fromkeys(evidence_ids))[:5]
    if not evidence_ids:
        return None
    try:
        from flowsint_crypto_compliance.platform.v2.gateway import (
            get_eccf_audit_trail as _get_eccf_audit_trail,
            verify_eccf_integrity as _verify_eccf_integrity,
        )

        rows: list[dict[str, Any]] = []
        for eid in evidence_ids:
            integrity = _verify_eccf_integrity(eid)
            audit = _get_eccf_audit_trail(eid)
            rows.append(
                {
                    "evidence_id": eid,
                    "integrity_ok": integrity.get("ok"),
                    "audit_entries": audit.get("count") or len(audit.get("entries") or []),
                }
            )
        if not rows:
            return None
        return {
            "heading_ru": "ECCF — целостность доказательств",
            "records": rows,
            "note_ru": "Сводка verify + audit trail по связанным evidence_id.",
        }
    except Exception:
        logger.debug("enterprise_sections: ECCF integrity skipped", exc_info=True)
        return None
