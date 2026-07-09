"""Forensic report enrichments: risk breakdown, timeline, graphs, signature, limitations."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.reporting.sanctions_screening import (
    build_screening_status,
    confidence_penalty_for_screening,
    sanctions_narrative_ru,
)

_ENGINE_VERSION = "FinSkalp Forensic Engine v1.3"
_GENERATION_NS = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

_SOURCE_DISPLAY: dict[str, str] = {
    "sovereign": "Суверенный узел FinSkalp",
    "trongrid": "TronGrid",
    "ledger": "Ledger",
    "tronscan": "TRONSCAN",
    "opensanctions": "OpenSanctions",
    "opensanctions_api": "OpenSanctions",
    "ofac_sdn": "OFAC",
    "ofac": "OFAC",
    "sovereign_registry": "Internal Registry",
    "kyt_import": "Internal Registry",
    "cospend_cluster": "Ledger",
    "unattributed": "Ledger",
    "screening": "Internal Registry",
    "ahmia": "Ahmia",
    "manual": "Manual analyst",
    "heuristic": "Behavioral heuristic",
}


def enrich_forensic_report(
    report: dict[str, Any],
    *,
    screening: dict[str, Any],
    attribution: dict[str, Any],
    evidence_sources: dict[str, Any],
    open_osint: dict[str, Any] | None = None,
    fusion_graph: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply all forensic AML-grade enrichments to v2 report dict."""
    source_status = {
        **(screening.get("source_status") or {}),
        **(attribution.get("source_status") or {}),
    }
    sanctions_hits = attribution.get("sanctions_hits") or []
    screening_status = build_screening_status(source_status=source_status, sanctions_hits=sanctions_hits)
    sanctions_narr = sanctions_narrative_ru(
        screening_status=screening_status,
        source_status=source_status,
        sanctions_hits=sanctions_hits,
    )

    onchain = screening.get("onchain_summary") or {}
    risk_score = float(screening.get("risk_score") or report.get("address_profile", {}).get("risk_score") or 0)

    breakdown = build_risk_score_breakdown(
        screening=screening,
        attribution=attribution,
        open_osint=open_osint,
        pattern=report.get("executive_summary", {}).get("pattern"),
    )
    enriched_connections = enrich_attribution_connections(attribution.get("connections") or [], onchain)
    counterparty_table = build_counterparty_distribution(enriched_connections, onchain, report.get("priority_tracing_lead"))
    timeline = build_activity_timeline(onchain, report.get("executive_summary", {}))
    flow_viz = build_flow_visualizations(
        address=report.get("address_profile", {}).get("address", ""),
        onchain=onchain,
        connections=enriched_connections,
        priority_lead=report.get("priority_tracing_lead"),
        fusion_graph=fusion_graph,
        risk_score=risk_score,
    )
    gs = dict(report.get("graph_section") or {})
    if fusion_graph and (fusion_graph.get("nodes") or []) and not gs.get("has_svg") and not gs.get("has_png"):
        from flowsint_crypto_compliance.reporting.graph_report import graph_section_for_report

        gs = graph_section_for_report(fusion_graph)
        report["graph_section"] = gs
    db_versions = build_database_versions(source_status, onchain)
    on_chain_meta = {
        "on_chain_source": onchain.get("on_chain_source"),
        "on_chain_source_ru": onchain.get("on_chain_source_ru"),
        "on_chain_is_sovereign": onchain.get("on_chain_is_sovereign"),
        "on_chain_failover": onchain.get("on_chain_failover"),
    }
    if onchain.get("on_chain_source_ru"):
        on_chain_meta["on_chain_badge_ru"] = (
            f"Источник on-chain: {onchain['on_chain_source_ru']}"
        )
    limitations = build_limitations_block(
        report=report,
        screening=screening,
        attribution=attribution,
        screening_status=screening_status,
        source_status=source_status,
        open_osint=open_osint,
    )
    overall_conf = compute_overall_confidence(
        attribution=attribution,
        screening_status=screening_status,
        source_status=source_status,
        screening=screening,
    )
    signature = build_digital_signature(report, evidence_sources)

    report["version"] = _ENGINE_VERSION
    report["screening_status"] = screening_status
    report["sanctions_screening"] = {
        **sanctions_narr,
        "screening_status": screening_status,
        "hits": sanctions_hits,
    }
    report["risk_score_breakdown"] = breakdown
    report["attribution_records"] = enriched_connections
    report["counterparty_distribution"] = counterparty_table
    report["activity_timeline"] = timeline
    report["flow_visualization"] = flow_viz
    report["database_versions"] = db_versions
    report["on_chain_source"] = on_chain_meta
    report["overall_attribution_confidence"] = overall_conf
    report["digital_signature"] = signature
    report["limitations_and_confidence"] = limitations
    report["forensic_language"] = apply_forensic_language(report)

    # Patch executive summary with forensic phrasing
    exec_sum = report.get("executive_summary") or {}
    exec_sum["key_findings_ru"] = _forensic_key_findings(report, breakdown, overall_conf, sanctions_narr)
    exec_sum["text_ru"] = report["forensic_language"].get("executive_summary_ru", exec_sum.get("text_ru", ""))
    report["executive_summary"] = exec_sum

    if report.get("address_profile"):
        report["address_profile"]["risk_score_breakdown_total"] = breakdown.get("total")

    return report


def build_risk_score_breakdown(
    *,
    screening: dict[str, Any],
    attribution: dict[str, Any],
    open_osint: dict[str, Any] | None,
    pattern: str | None,
) -> dict[str, Any]:
    """Explain risk score as weighted components summing to total."""
    total = float(screening.get("risk_score") or 0)
    onchain = screening.get("onchain_summary") or {}
    findings = screening.get("findings") or []
    kyt = onchain.get("kyt_exposure") or {}

    registry_pts = min(40.0, 8.0 * sum(1 for f in findings if "реестр" in str(f.get("title_ru", "")).lower()))
    if attribution.get("sanctions_hits"):
        registry_pts = max(registry_pts, 35.0)

    behavioral_pts = 12.0 if pattern == "funnel_consolidation" else 6.0 if pattern == "dispersal" else 4.0
    cp_exposure = min(25.0, float(kyt.get("connection_count") or 0) * 1.5)
    fan_pts = min(15.0, abs(onchain.get("inbound_count", 0) - onchain.get("outbound_count", 0)) * 0.8)
    osint_pts = min(12.0, float((open_osint or {}).get("open_risk_score") or 0) * 0.12)
    darknet_pts = min(8.0, sum(1 for m in (open_osint or {}).get("mentions") or [] if m.get("source_type") == "darknet") * 2.0)
    sanctions_pts = min(10.0, len(attribution.get("sanctions_hits") or []) * 5.0)

    raw_components = [
        ("Registry match", registry_pts, "Tier-1/Tier-2 label or registry finding"),
        ("Behavioral heuristics", behavioral_pts, "Funnel/dispersal pattern heuristics (Tier-3)"),
        ("Counterparty exposure", cp_exposure, "Labeled inbound/outbound counterparties"),
        ("High fan-in/out", fan_pts, "Inbound vs outbound transaction count asymmetry"),
        ("OSINT correlation", osint_pts, "Open OSINT / Scalpel mention risk score"),
        ("Darknet mentions", darknet_pts, "Ahmia / darknet index signals"),
        ("Sanctions screening", sanctions_pts, "Confirmed or store-level sanctions hits"),
    ]
    raw_sum = sum(c[1] for c in raw_components) or 1.0
    scale = total / raw_sum if total > 0 else 1.0

    components = []
    for name, pts, explanation in raw_components:
        weighted = round(pts * scale, 1)
        pct = round(100 * weighted / total, 1) if total > 0 else 0.0
        components.append(
            {
                "component": name,
                "points": weighted,
                "pct": pct,
                "explanation_ru": explanation,
            }
        )

    return {
        "total": round(total, 1),
        "components": components,
        "methodology_ru": "Взвешенная декомпозиция эвристического risk score; не является юридическим выводом.",
    }


def _normalize_source(raw: str | None) -> str:
    if not raw:
        return "Ledger"
    key = str(raw).lower().replace("attr_", "")
    for prefix, label in _SOURCE_DISPLAY.items():
        if prefix in key:
            return label
    return _SOURCE_DISPLAY.get(key, raw.replace("_", " ").title())


def enrich_attribution_connections(connections: list[dict], onchain: dict) -> list[dict]:
    """Add source, verification level, evidence fields to each connection."""
    tx_times: dict[str, list[int]] = {}
    for tx in onchain.get("sample_tx") or []:
        cp = tx.get("counterparty")
        ts = tx.get("timestamp")
        if cp and ts:
            tx_times.setdefault(cp, []).append(int(ts))

    out = []
    for c in connections:
        addr = c.get("address") or ""
        tier = int(c.get("tier") or 3)
        verification = "Tier-1 verified" if tier == 1 else "Tier-2 single-source" if tier == 2 else "Tier-3 heuristic"
        times = tx_times.get(addr, [])
        first_seen = _fmt_ts(min(times)) if times else onchain.get("first_activity")
        last_seen = _fmt_ts(max(times)) if times else onchain.get("last_activity")
        out.append(
            {
                **c,
                "source_display": _normalize_source(c.get("source")),
                "verification_level": verification,
                "evidence": c.get("evidence") or f"ledger:{addr[:12]}…",
                "confidence_pct": round(float(c.get("confidence") or 0) * 100, 1),
                "first_seen": first_seen,
                "last_seen": last_seen,
                "relationship": _relationship_label(c),
            }
        )
    return out


def _relationship_label(conn: dict) -> str:
    beh = str(conn.get("behavior") or "transfer").lower()
    if beh == "indirect":
        return "Indirect exposure"
    if conn.get("hops", 1) > 1:
        return f"Indirect ({conn.get('hops')} hop)"
    return "Direct counterparty"


def build_counterparty_distribution(
    connections: list[dict],
    onchain: dict,
    priority_lead: dict | None,
) -> list[dict]:
    rows = []
    for c in connections[:25]:
        rows.append(
            {
                "counterparty": c.get("entity_name") or c.get("address", "")[:16],
                "address": c.get("address"),
                "amount": round(float(c.get("total_received") or 0), 4),
                "risk": c.get("risk_tier") or "—",
                "tier": c.get("tier"),
                "first_seen": c.get("first_seen"),
                "last_seen": c.get("last_seen"),
                "relationship": c.get("relationship"),
                "source": c.get("source_display"),
                "verification_level": c.get("verification_level"),
            }
        )
    if priority_lead and priority_lead.get("lead_address"):
        la = priority_lead["lead_address"]
        if not any(r.get("address") == la for r in rows):
            rows.insert(
                0,
                {
                    "counterparty": "Priority destination",
                    "address": la,
                    "amount": priority_lead.get("amount"),
                    "risk": "HIGH",
                    "tier": 2,
                    "first_seen": priority_lead.get("lead_created_at"),
                    "last_seen": onchain.get("last_activity"),
                    "relationship": "Sweep / consolidation outflow",
                    "source": _normalize_source(priority_lead.get("data_source")),
                    "verification_level": "Tier-2 ledger-confirmed",
                },
            )
    return rows


def build_activity_timeline(onchain: dict, exec_sum: dict) -> list[dict]:
    """Chronological narrative steps for forensic timeline section."""
    inbound_n = onchain.get("inbound_count", 0)
    outbound_n = onchain.get("outbound_count", 0)
    first = onchain.get("first_activity") or "—"
    last = onchain.get("last_activity") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    steps = [
        {"ts": first, "label_ru": f"{inbound_n} inbound transaction(s) observed", "label_en": "Inbound activity"},
    ]
    if exec_sum.get("pattern") == "funnel_consolidation":
        steps.append({"ts": "—", "label_ru": "Consolidation pattern (funnel)", "label_en": "Consolidation"})
    if outbound_n:
        steps.append(
            {"ts": "—", "label_ru": f"{outbound_n} outbound transaction(s)", "label_en": "Outbound activity"}
        )
        if exec_sum.get("pattern") == "funnel_consolidation":
            steps.append({"ts": "—", "label_ru": "Sweep transaction to priority destination", "label_en": "Sweep"})
    steps.append({"ts": last, "label_ru": "Current on-chain state at report time", "label_en": "Current state"})
    return steps


def _risk_color(score: float) -> str:
    from flowsint_crypto_compliance.reporting.svg_graph_style import risk_node_color

    return risk_node_color(score)


def build_flow_visualizations(
    *,
    address: str,
    onchain: dict,
    connections: list[dict],
    priority_lead: dict | None,
    fusion_graph: dict[str, Any] | None,
    risk_score: float,
) -> dict[str, Any]:
    """Flow graph (DOT + SVG) and Sankey diagram."""
    inbound = [c for c in connections if c.get("behavior") != "indirect"][:8]
    outbound_addr = (priority_lead or {}).get("lead_address")
    subject = address[:10] + "…" if len(address) > 12 else address

    dot_lines = [
        "digraph finskalp_flow {",
        '  rankdir=LR; node [shape=box, style=filled, fontname="Arial"];',
        f'  subject [label="Subject\\n{subject}", fillcolor="{_risk_color(risk_score)}", fontcolor=white];',
    ]
    for i, c in enumerate(inbound[:6]):
        nid = f"in{i}"
        rs = float(c.get("risk_pct") or 15)
        dot_lines.append(
            f'  {nid} [label="{c.get("entity_name", nid)[:20]}", fillcolor="{_risk_color(rs)}"];'
        )
        dot_lines.append(f"  {nid} -> subject;")
    if outbound_addr:
        dot_lines.append(
            f'  dest [label="Priority dest\\n{outbound_addr[:10]}…", fillcolor="#6366f1"];'
        )
        dot_lines.append("  subject -> dest;")
    dot_lines.append("}")
    dot_source = "\n".join(dot_lines)

    svg = _simple_flow_svg(subject, inbound[:5], outbound_addr, risk_score)
    sankey_svg = _simple_sankey_svg(inbound[:4], subject, outbound_addr, onchain)

    nx_note = None
    try:
        import networkx as nx  # noqa: F401

        nx_note = "NetworkX available for extended graph analytics"
    except ImportError:
        nx_note = "NetworkX not installed; DOT/SVG heuristic layout used"

    fusion_nodes = fusion_graph.get("nodes") or [] if fusion_graph else []
    fusion_edges = fusion_graph.get("edges") or [] if fusion_graph else []
    return {
        "dot_source": dot_source,
        "svg": svg,
        "sankey_svg": sankey_svg,
        "engine_note": nx_note,
        "has_svg": bool(svg),
        "has_sankey": bool(sankey_svg),
        "fusion_linked": bool(fusion_nodes),
        "fusion_node_count": len(fusion_nodes),
        "fusion_edge_count": len(fusion_edges),
    }


def _simple_flow_svg(subject: str, inbound: list[dict], outbound: str | None, risk: float) -> str:
    from flowsint_crypto_compliance.reporting.svg_graph_style import (
        risk_node_color,
        svg_background,
        svg_dashed_edge,
        svg_defs,
        svg_node_circle,
        svg_title,
    )

    w, h = 520, 240
    subj_color = risk_node_color(risk, is_subject=True)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        svg_defs(),
        svg_background(w, h),
        svg_title(w, "Counterparty flow", y=18),
    ]
    x_subj, y_subj = 270, h / 2
    subj_r = 30.0
    for i, c in enumerate(inbound):
        y = 42 + i * 38
        x = 72
        rc = risk_node_color(float(c.get("risk_pct") or 20))
        label = (c.get("entity_name") or "CP")[:14]
        r = 14.0
        parts.append(svg_dashed_edge(x + r, y, x_subj - subj_r, y_subj + (y - y_subj) * 0.15))
        parts.append(svg_node_circle(x, y, radius=r, fill=rc, label=label, label_side="left"))
    if outbound:
        ox, oy = 448, h / 2
        parts.append(svg_dashed_edge(x_subj + subj_r, y_subj, ox - 14, oy))
        parts.append(
            svg_node_circle(ox, oy, radius=14, fill="#7c3aed", label="Priority", label_side="right")
        )
    parts.append(
        svg_node_circle(x_subj, y_subj, radius=subj_r, fill=subj_color, label=subject, label_side="center")
    )
    parts.append("</svg>")
    return "".join(parts)


def _simple_sankey_svg(inbound: list[dict], subject: str, outbound: str | None, onchain: dict) -> str:
    from flowsint_crypto_compliance.reporting.svg_graph_style import (
        risk_node_color,
        svg_background,
        svg_defs,
        svg_node_circle,
        svg_title,
    )

    w, h = 480, 220
    gross_in = float(onchain.get("inbound_amount") or 1)
    gross_out = float(onchain.get("outbound_amount") or 0)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        svg_defs(),
        svg_background(w, h),
        svg_title(w, "Value flow (Sankey heuristic)", y=18),
    ]
    subj_x, subj_y = 290, h / 2
    for i, c in enumerate(inbound):
        y = 38 + i * 42
        amt = float(c.get("total_received") or 0)
        bw = max(3, min(24, int(24 * amt / gross_in))) if gross_in else 8
        rc = risk_node_color(float(c.get("risk_pct") or 20))
        parts.append(f'<rect x="24" y="{y}" width="56" height="{bw}" rx="3" fill="{rc}" opacity="0.9"/>')
        parts.append(
            f'<path d="M 80 {y + bw / 2} C 160 {y + bw / 2}, 210 {subj_y}, {subj_x - 28} {subj_y}" '
            f'stroke="#ffffff" fill="none" stroke-width="{max(1.5, bw / 3):.1f}" '
            f'stroke-dasharray="5,4" opacity="0.75"/>'
        )
    parts.append(
        svg_node_circle(subj_x, subj_y, radius=24, fill=risk_node_color(50, is_subject=True), label=subject, label_side="center")
    )
    if outbound and gross_out:
        parts.append(
            f'<path d="M {subj_x + 28} {subj_y} C 360 {subj_y}, 390 {subj_y}, 420 {subj_y}" '
            f'stroke="#ffffff" fill="none" stroke-width="6" stroke-dasharray="5,4" opacity="0.75"/>'
        )
        parts.append(
            svg_node_circle(438, subj_y, radius=12, fill="#7c3aed", label="Out", label_side="right")
        )
    parts.append("</svg>")
    return "".join(parts)


def _blockchain_height_label(onchain: dict) -> str:
    if onchain.get("on_chain_is_sovereign"):
        return "latest (суверенный узел FinSkalp)"
    if onchain.get("on_chain_failover"):
        return "latest (TronGrid failover)"
    return "latest (TronGrid confirmed)"


def build_database_versions(source_status: dict, onchain: dict) -> dict[str, Any]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return {
        "registry_snapshot": source_status.get("registry_primary", "embedded_bootstrap"),
        "osint_snapshot": source_status.get("attr_opensanctions_api", "—"),
        "sanctions_snapshot": f"OFAC bootstrap + OpenSanctions API ({source_status.get('opensanctions_api', '—')})",
        "blockchain_height": onchain.get("block_height") or _blockchain_height_label(onchain),
        "generated_at": now,
        "engine_version": _ENGINE_VERSION,
    }


def compute_overall_confidence(
    *,
    attribution: dict,
    screening_status: dict[str, str],
    source_status: dict[str, str],
    screening: dict,
) -> dict[str, Any]:
    tier = attribution.get("tier_summary") or {}
    t1 = tier.get("tier_1", 0)
    t2 = tier.get("tier_2", 0)
    t3 = tier.get("tier_3", 0)
    base = 0.35
    base += min(0.25, t1 * 0.08)
    base += min(0.15, t2 * 0.04)
    base -= min(0.1, t3 * 0.02)
    if source_status.get("onchain") == "ok":
        base += 0.12
    if screening.get("evidence_chain"):
        base += 0.05
    base -= confidence_penalty_for_screening(screening_status)
    pct = round(max(0.15, min(0.98, base)) * 100, 1)
    if pct >= 80:
        label = "High"
    elif pct >= 55:
        label = "Moderate"
    else:
        label = "Low"
    return {
        "label": label,
        "label_ru": {"High": "Высокая", "Moderate": "Умеренная", "Low": "Низкая"}[label],
        "pct": pct,
        "factors_ru": [
            f"Tier-1 labels: {t1}; Tier-2: {t2}; Tier-3: {t3}",
            f"OpenSanctions: {screening_status.get('OpenSanctions')}",
            f"OFAC: {screening_status.get('OFAC')}",
        ],
    }


def build_limitations_block(
    *,
    report: dict,
    screening: dict,
    attribution: dict,
    screening_status: dict,
    source_status: dict,
    open_osint: dict | None,
) -> dict[str, Any]:
    items: list[str] = []
    unavailable_apis = [
        k for k, v in source_status.items() if str(v).startswith(("degraded", "error"))
    ]
    if unavailable_apis:
        items.append(f"✔ Недоступные API: {', '.join(unavailable_apis[:6])}")
    if screening_status.get("OpenSanctions") == "unavailable":
        items.append("✔ OpenSanctions live screening unavailable — negative sanctions inference not valid")
    if not attribution.get("connections"):
        items.append("✔ Отсутствуют размеченные контрагенты — exposure может быть неполным")
    tier3 = (attribution.get("tier_summary") or {}).get("tier_3", 0)
    if tier3:
        items.append(f"✔ {tier3} эвристических (Tier-3) атрибуций — не подтверждены независимо")
    items.append("✔ Предположительные выводы помечены Tier-2/Tier-3; ownership не установлен")
    items.append(
        "✔ Уровень достоверности: см. Overall Attribution Confidence; "
        "controller identification не выполняется"
    )
    items.extend(report.get("limitations_and_confidence", {}).get("items") or [])
    if (open_osint or {}).get("noise_filter", {}).get("rejected_count"):
        items.append("✔ OSINT noise filter отсеял часть сигналов")

    return {
        "items": items,
        "controller_identification_ru": (
            "Cannot independently confirm ownership. "
            "Observed on-chain behavior is consistent with labeled patterns; "
            "legal entity / natural person identification requires VASP/bank inquiry under 115-FZ."
        ),
        "source_status": source_status,
        "screening_status": screening_status,
    }


def build_digital_signature(report: dict[str, Any], evidence_sources: dict[str, Any]) -> dict[str, Any]:
    report_uuid = str(uuid.uuid5(_GENERATION_NS, f"{report.get('case_ref')}:{report.get('report_id')}"))
    generation_id = hashlib.sha256(
        f"{report.get('report_id')}:{report.get('generated_at')}".encode()
    ).hexdigest()[:16].upper()

    canonical = {
        "case_ref": report.get("case_ref"),
        "report_id": report.get("report_id"),
        "address": (report.get("address_profile") or {}).get("address"),
        "generated_at": report.get("generated_at"),
        "risk_score": (report.get("address_profile") or {}).get("risk_score"),
    }
    report_hash = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    bundle_hash = hashlib.sha256(
        json.dumps(evidence_sources, sort_keys=True, default=str).encode()
    ).hexdigest()

    sig_block: dict[str, Any] = {
        "report_uuid": report_uuid,
        "generation_id": generation_id,
        "engine_version": _ENGINE_VERSION,
        "report_sha256": report_hash,
        "evidence_bundle_sha256": bundle_hash,
        "signature_algorithm": None,
        "signature_value": None,
    }

    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        # Demo key derived from case — production should use HSM/vault
        seed = hashlib.sha256(b"finskalp-demo-ed25519-seed").digest()
        key = Ed25519PrivateKey.from_private_bytes(seed)
        signed = key.sign(report_hash.encode())
        sig_block["signature_algorithm"] = "Ed25519"
        sig_block["signature_value"] = signed.hex()
        sig_block["signature_note"] = "Demo Ed25519 — replace with production key in deployment"
    except Exception:
        sig_block["signature_note"] = "Ed25519 signing unavailable (install cryptography package)"

    return sig_block


def apply_forensic_language(report: dict[str, Any]) -> dict[str, str]:
    ap = report.get("address_profile") or {}
    pattern_ru = (report.get("executive_summary") or {}).get("pattern_ru", "")
    addr = ap.get("address", "")
    risk = ap.get("risk_score", 0)

    exec_ru = (
        f"Observed on-chain activity for address {addr} ({ap.get('network', '')}) "
        f"is indicative of a {pattern_ru.lower() if pattern_ru else 'standard flow'} pattern. "
        f"Risk score {risk}/100 reflects weighted heuristics; "
        f"cannot independently confirm ownership or illicit intent without corroborating evidence."
    )
    return {"executive_summary_ru": exec_ru}


def _forensic_key_findings(
    report: dict,
    breakdown: dict,
    overall_conf: dict,
    sanctions_narr: dict,
) -> list[str]:
    items = [
        f"Risk score: {breakdown.get('total', 0)}/100 (see Risk Score Breakdown)",
        f"Overall attribution confidence: {overall_conf.get('label')} ({overall_conf.get('pct')}%)",
        sanctions_narr.get("status_en") or sanctions_narr.get("status_ru", ""),
    ]
    pattern = (report.get("executive_summary") or {}).get("pattern_ru")
    if pattern:
        items.append(f"Pattern matches: {pattern} (Tier-3 heuristic)")
    lead = report.get("priority_tracing_lead")
    if lead:
        items.append(
            f"Observed behavior consistent with consolidation toward "
            f"{str(lead.get('lead_address', ''))[:16]}… ({lead.get('pct_of_outflow')}%)"
        )
    return items


def _fmt_ts(ts: int | str | None) -> str:
    if ts is None:
        return "—"
    try:
        v = int(ts)
        if v < 10_000_000_000:
            v *= 1000
        return datetime.fromtimestamp(v / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except (TypeError, ValueError):
        return str(ts)
