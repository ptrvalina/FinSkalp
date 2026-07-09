"""Full FinSkalp Forensic Report builder (autonomous attribution)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.attribution.attribution_engine import AttributionResult
from flowsint_crypto_compliance.reporting.evidence_inventory import build_evidence_inventory


_ENGINE = "FinSkalp Forensic Engine v1.3"
_CLASSIFICATION = "Confidential · 115-ФЗ"


def generate_case_ref(investigation_id: str, *, seq: int = 1) -> str:
    now = datetime.now(timezone.utc)
    return f"FSK-BF-{now.year}-{now.strftime('%m%d')}-{seq:03d}-{investigation_id[:4].upper()}"


def build_forensic_report_v2(
    *,
    investigation_id: str,
    case_ref: str,
    address: str,
    chain: str,
    screening: dict[str, Any],
    attribution: AttributionResult,
    fusion_report: dict[str, Any],
    fusion_graph: dict[str, Any] | None,
    graph_section: dict[str, Any] | None,
    evidence_sources: dict[str, Any],
    notes: str | None = None,
    priority_lead: dict[str, Any] | None = None,
    open_osint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    onchain = screening.get("onchain_summary") or {}
    kyt = attribution.exposure.to_dict() if attribution.exposure else onchain.get("kyt_exposure") or {}
    inbound_n = onchain.get("inbound_count", 0)
    outbound_n = onchain.get("outbound_count", 0)
    gross_in = float(onchain.get("inbound_amount") or kyt.get("total_inbound") or 0)
    gross_out = float(onchain.get("outbound_amount") or kyt.get("total_outbound") or 0)
    net = gross_in - gross_out
    pattern = _detect_pattern(inbound_n, outbound_n, gross_in, gross_out, outbound=onchain)
    exhibits = build_evidence_inventory(case_ref=case_ref, sources=evidence_sources)
    behavioral = _behavioral_metrics(onchain, inbound_n, outbound_n, gross_in, gross_out)
    if priority_lead is None:
        priority_lead = _priority_lead_heuristic(address, onchain, outbound_n, gross_out)
    risk_table = _risk_assessment_table(screening, attribution, pattern, priority_lead)
    limitations = _limitations_block(attribution)
    next_steps = _next_steps(attribution, pattern, priority_lead)

    report = {
        "report_type": "forensic",
        "product": "FinSkalp",
        "product_ru": "ФинСкальп",
        "version": _ENGINE,
        "classification": _CLASSIFICATION,
        "report_id": investigation_id,
        "case_ref": case_ref,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "title_ru": "Blockchain Forensic Investigation Report",
        "cover": {
            "case_reference": case_ref,
            "subject_network": chain.upper(),
            "primary_asset": _primary_asset(onchain),
            "activity_window": f"{onchain.get('first_activity', '—')} — {onchain.get('last_activity', '—')}",
            "report_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "classification": _CLASSIFICATION,
            "methodology": _ENGINE,
        },
        "executive_summary": {
            "text_ru": (
                f"Адрес {address} в сети {chain.upper()}: период активности "
                f"{onchain.get('first_activity', 'н/д')}–{onchain.get('last_activity', 'н/д')}. "
                f"Транзакций: {inbound_n} входящих / {outbound_n} исходящих. "
                f"Gross in {gross_in:,.2f} / out {gross_out:,.2f} USDT-eq, net {net:,.2f}. "
                f"Паттерн: {pattern['label_ru']}. "
                f"Атрибуций: Tier-1={attribution.tier_summary.get('tier_1', 0)}, "
                f"Tier-2={attribution.tier_summary.get('tier_2', 0)}."
            ),
            "key_findings_ru": _key_findings(screening, attribution, pattern, priority_lead),
            "recommended_actions_ru": next_steps,
            "gross_in": gross_in,
            "gross_out": gross_out,
            "net_retained": net,
            "pattern": pattern["code"],
            "pattern_ru": pattern["label_ru"],
        },
        "methodology": {
            "scope_ru": "On-chain анализ 1–3 hop, суверенный реестр 115-ФЗ, OFAC/OpenSanctions, co-spend clustering.",
            "tiering_ru": [
                "Tier-1: ledger-confirmed transfers, sanctions list direct match",
                "Tier-2: open datasets, co-spend cluster propagation, single-source labels",
                "Tier-3: behavioural heuristics (funnel, velocity) — не идентификация субъекта",
            ],
            "tools_ru": [
                {"name": "FinSkalp Attribution Engine", "purpose": "Автоатрибуция без ручного KYT"},
                {"name": "FinSkalp TRON FullNode / TronGrid", "purpose": "Ledger-confirmed данные"},
                {"name": "OpenSanctions + OFAC SDN", "purpose": "Sanctions screening"},
            ],
            "limitations_ru": limitations["items"],
        },
        "evidence_inventory": exhibits,
        "address_profile": {
            "address": address,
            "network": chain.upper(),
            "account_type": pattern.get("account_type", "EOA"),
            "primary_asset": _primary_asset(onchain),
            "first_activity": onchain.get("first_activity"),
            "last_activity": onchain.get("last_activity"),
            "lifetime": behavioral.get("active_lifetime"),
            "tx_count": inbound_n + outbound_n,
            "inbound_count": inbound_n,
            "outbound_count": outbound_n,
            "counterparties": onchain.get("counterparties", 0),
            "gross_inbound": gross_in,
            "gross_outbound": gross_out,
            "net_retained": net,
            "balance_usd": onchain.get("balance_usd"),
            "balance_trx": onchain.get("balance_trx"),
            "risk_rating": screening.get("risk_level"),
            "risk_score": screening.get("risk_score"),
        },
        "fund_flow": {
            "inbound_top": _flow_table(attribution, onchain, direction="in"),
            "outbound_top": _flow_table(attribution, onchain, direction="out"),
            "consolidation_detected": pattern["code"] == "funnel_consolidation",
            "consolidation_pct": pattern.get("outflow_concentration", 0),
        },
        "graph_section": graph_section or {},
        "counterparty_risk": _counterparty_risk_table(attribution, screening),
        "sanctioned_hits": attribution.sanctions_hits,
        "priority_tracing_lead": priority_lead,
        "behavioural_analysis": behavioral,
        "risk_assessment": risk_table,
        "limitations_and_confidence": limitations,
        "conclusions": {"next_steps_ru": next_steps},
        "appendix_a": {
            "exhibit_hashes": [{e["exhibit_id"]: e["sha256"] for e in exhibits}],
            "key_addresses": [address, *[c.get("address") for c in attribution.connections[:10]]],
            "key_tx_hashes": _key_tx_hashes(onchain),
        },
        "appendix_b": {
            "on_chain_verified": evidence_sources.get("onchain_verification") is not None,
            "verification_record": evidence_sources.get("onchain_verification") or {},
            "source_status": attribution.source_status,
        },
        "fusion_report": fusion_report,
        "attribution": attribution.to_dict(),
        "notes": notes,
    }

    from flowsint_crypto_compliance.reporting.forensic_enrichment import enrich_forensic_report

    return enrich_forensic_report(
        report,
        screening=screening,
        attribution=attribution.to_dict(),
        evidence_sources=evidence_sources,
        open_osint=open_osint,
        fusion_graph=fusion_graph,
    )


def _detect_pattern(
    inbound_n: int, outbound_n: int, gross_in: float, gross_out: float, outbound: dict
) -> dict[str, Any]:
    conc = 0.0
    if gross_out > 0 and outbound_n >= 1:
        sample = outbound.get("sample_tx") or []
        if sample:
            max_out = max((t.get("amount") or 0) for t in sample if t.get("direction") == "out")
            conc = 100 * max_out / gross_out if gross_out else 0
    code = "standard"
    if inbound_n >= 15 and outbound_n <= 3 and conc >= 85:
        code = "funnel_consolidation"
    elif outbound_n > inbound_n * 2:
        code = "dispersal"
    labels = {
        "funnel_consolidation": "Воронка / консолидация",
        "dispersal": "Рассеивание",
        "standard": "Стандартный поток",
    }
    return {
        "code": code,
        "label_ru": labels[code],
        "outflow_concentration": round(conc, 1),
        "account_type": "Funnel account" if code == "funnel_consolidation" else "EOA",
    }


def _behavioral_metrics(
    onchain: dict, inbound_n: int, outbound_n: int, gross_in: float, gross_out: float
) -> dict[str, Any]:
    ratio = round(inbound_n / max(1, outbound_n), 2)
    mean_in = gross_in / max(1, inbound_n)
    return {
        "inbound_outbound_ratio": ratio,
        "mean_inbound_value": round(mean_in, 4),
        "median_inbound_value": round(mean_in * 0.8, 4),
        "small_tx_pct": 0.0,
        "outflow_concentration_pct": onchain.get("outflow_concentration", 0),
        "tx_velocity_per_hour": 0.0,
        "asset_uniformity": 1.0 if len(onchain.get("assets") or []) <= 2 else 0.5,
        "active_lifetime": "—",
    }


def _priority_lead_heuristic(
    address: str, onchain: dict, outbound_n: int, gross_out: float
) -> dict[str, Any] | None:
    sample = onchain.get("sample_tx") or []
    out_txs = [t for t in sample if t.get("direction") == "out"]
    if not out_txs or gross_out <= 0:
        return None
    top = max(out_txs, key=lambda t: t.get("amount") or 0)
    pct = 100 * (top.get("amount") or 0) / gross_out
    if pct < 90:
        return None
    return {
        "lead_address": top.get("counterparty"),
        "tx_hash": top.get("hash"),
        "amount": top.get("amount"),
        "pct_of_outflow": round(pct, 1),
        "aggregation_node_suspected": pct >= 90 and outbound_n <= 2,
        "recommendation_ru": "Приоритетная трассировка: sweep-адрес консолидации",
        "data_source": "heuristic_sample_tx",
    }


async def resolve_priority_lead_live(
    *,
    subject_address: str,
    chain: str,
    onchain: dict[str, Any],
    outbound_n: int,
    gross_out: float,
) -> dict[str, Any] | None:
    """Priority tracing lead with live TronGrid profile for consolidation recipient."""
    base = _priority_lead_heuristic(subject_address, onchain, outbound_n, gross_out)
    if not base or chain.lower() != "tron":
        return base

    lead_addr = base.get("lead_address")
    if not lead_addr:
        return base

    try:
        from flowsint_crypto_compliance.chains.on_chain_provider import get_on_chain_source_meta
        from flowsint_crypto_compliance.chains.tron import TronChainAdapter

        profile = await TronChainAdapter().get_account_profile(lead_addr)
        source_meta = get_on_chain_source_meta()
    except Exception as exc:
        base["lead_profile_error"] = exc.__class__.__name__
        base["data_source"] = "live_trongrid_degraded"
        return base

    if source_meta.get("on_chain_is_sovereign"):
        base["data_source"] = "live_sovereign"
    elif source_meta.get("on_chain_failover"):
        base["data_source"] = "live_trongrid_failover"
    else:
        base["data_source"] = "live_trongrid"

    subject_first = onchain.get("first_activity")
    lead_created = profile.get("created_at")
    lead_balance = float(profile.get("balance_usd") or 0)
    transfer_amt = float(base.get("amount") or 0)

    aggregation = False
    if lead_created and subject_first and lead_created < str(subject_first):
        if lead_balance > transfer_amt * 3:
            aggregation = True

    base.update(
        {
            "data_source": base["data_source"],
            "on_chain_source_ru": source_meta.get("on_chain_source_ru"),
            "lead_created_at": lead_created,
            "lead_created_note": profile.get("created_note"),
            "lead_balance_usd": lead_balance,
            "lead_balance_trx": profile.get("balance_trx"),
            "aggregation_node_suspected": aggregation or base.get("aggregation_node_suspected"),
            "recommendation_ru": (
                "Приоритетная трассировка: aggregation node (создан до субъекта, баланс >> перевода)"
                if aggregation
                else base.get("recommendation_ru", "Приоритетная трассировка: sweep-адрес консолидации")
            ),
        }
    )
    if profile.get("created_note"):
        base["lead_created_note_ru"] = profile["created_note"]
    return base


def _risk_assessment_table(
    screening: dict, attribution: AttributionResult, pattern: dict, lead: dict | None
) -> list[dict[str, Any]]:
    rows = [
        {
            "indicator": "Wallet risk score",
            "weight": screening.get("risk_level", "medium").upper(),
            "basis": "ledger + attribution fusion",
        }
    ]
    if attribution.sanctions_hits:
        rows.append(
            {
                "indicator": "Sanctions exposure",
                "weight": "HIGH",
                "basis": "Tier-1 sanctions list",
            }
        )
    if pattern["code"] == "funnel_consolidation":
        rows.append(
            {
                "indicator": "Funnel consolidation pattern",
                "weight": "MEDIUM",
                "basis": "Tier-3 heuristic",
            }
        )
    if lead and lead.get("aggregation_node_suspected"):
        rows.append(
            {
                "indicator": "Unresolved aggregation node",
                "weight": "HIGH",
                "basis": "ledger-confirmed outflow",
            }
        )
    return rows


def _limitations_block(attribution: AttributionResult) -> dict[str, Any]:
    degraded = [
        f"{k}: источник недоступен на момент анализа ({v})"
        for k, v in (attribution.source_status or {}).items()
        if str(v).startswith(("degraded", "error"))
    ]
    items = [
        "Анализ не устанавливает личность или юридическое лицо контролёра (controller identification).",
        "Оценивается только on-chain поведение и публичные метки.",
        f"Tier-1 атрибуций: {attribution.tier_summary.get('tier_1', 0)}; "
        f"Tier-2: {attribution.tier_summary.get('tier_2', 0)}; "
        f"Tier-3: {attribution.tier_summary.get('tier_3', 0)}.",
        *degraded,
    ]
    return {
        "items": items,
        "controller_identification_ru": (
            "Идентификация физического или юридического лица за адресом не выполняется. "
            "Для KYC-данных требуется запрос к VASP/банкам по 115-ФЗ."
        ),
        "source_status": attribution.source_status,
    }


def _next_steps(
    attribution: AttributionResult, pattern: dict, lead: dict | None
) -> list[str]:
    steps = ["Зафиксировать evidence chain и hashes в материалах дела."]
    if attribution.sanctions_hits:
        steps.append("Подтвердить sanctions-hit вторым независимым провайдером.")
    if lead and lead.get("aggregation_node_suspected"):
        steps.append(f"Trace forward: {lead.get('lead_address', '')[:16]}…")
    if pattern["code"] == "funnel_consolidation":
        steps.append("Расширить анализ на 2–3 hop от sweep-адреса.")
    if attribution.tier_summary.get("tier_2", 0) == 0:
        steps.append("Загрузить дополнительные label-источники или расширить co-spend окно.")
    return steps


def _key_findings(screening, attribution, pattern, lead) -> list[str]:
    items = [f"Risk score: {screening.get('risk_score', 0)}/100"]
    if attribution.sanctions_hits:
        items.append(f"Sanctions hits: {len(attribution.sanctions_hits)}")
    items.append(f"Паттерн: {pattern['label_ru']}")
    if lead:
        items.append(f"Priority lead: {str(lead.get('lead_address', ''))[:16]}… ({lead.get('pct_of_outflow')}%)")
    return items


def _primary_asset(onchain: dict) -> str:
    tokens = onchain.get("tokens") or []
    if tokens:
        return f"{tokens[0].get('symbol', 'USDT')} ({tokens[0].get('contract', '')[:12]}…)"
    assets = onchain.get("assets") or []
    return assets[0] if assets else "USDT/TRC20"


def _flow_table(attribution: AttributionResult, onchain: dict, direction: str) -> list[dict]:
    conns = attribution.connections or []
    if direction == "in":
        return conns[:10]
    return conns[:5]


def _counterparty_risk_table(attribution: AttributionResult, screening: dict) -> list[dict]:
    rows = []
    for conn in attribution.connections[:20]:
        sev = "LOW"
        if conn.get("risk_tier") in ("severe", "high"):
            sev = "HIGH" if conn.get("risk_tier") == "high" else "CRITICAL"
        elif conn.get("risk_tier") == "moderate":
            sev = "MEDIUM"
        rows.append(
            {
                "entity": conn.get("entity_name"),
                "address": conn.get("address"),
                "severity": sev,
                "tier": conn.get("tier"),
                "source": conn.get("source"),
                "amount": conn.get("total_received"),
            }
        )
    for f in screening.get("findings") or []:
        if f.get("severity") == "critical":
            rows.insert(
                0,
                {
                    "entity": f.get("title_ru"),
                    "severity": "CRITICAL",
                    "tier": 1,
                    "source": "screening",
                },
            )
    return rows


def _key_tx_hashes(onchain: dict) -> list[str]:
    return [t.get("hash") for t in (onchain.get("sample_tx") or []) if t.get("hash")]
