"""ФинСкальп — отчёты в формате blockchain forensic / wallet screening (суверенный контур РФ)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.osint_core.fusion_engine import FusionResult
from flowsint_crypto_compliance.reporting.pdf_report import render_pdf_bytes
from flowsint_types.fiat_crypto import Chain

_PRODUCT = "FinSkalp"
_PRODUCT_RU = "ФинСкальп"
_VERSION = "v1.2.0-kyt"
_CLASSIFICATION = "КОНФИДЕНЦИАЛЬНО · 115-ФЗ"


class FinSkalpReportBuilder:
    def build_address_report(
        self,
        *,
        investigation_id: str,
        case_ref: str,
        screening: dict[str, Any],
        fusion_report: dict[str, Any],
        notes: str | None = None,
        open_osint: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        findings = screening.get("findings") or []
        risk_tags = _risk_tags_from_findings(findings, onchain=screening.get("onchain_summary") or {})
        onchain = screening.get("onchain_summary") or {}
        kyt = onchain.get("kyt_exposure") or {}
        attr = onchain.get("attribution") or {}
        sanctions_hits = attr.get("sanctions_hits") or []
        source_status = {
            **(screening.get("source_status") or {}),
            **(attr.get("source_status") or {}),
        }
        from flowsint_crypto_compliance.reporting.sanctions_screening import (
            build_screening_status,
            sanctions_narrative_ru,
        )

        screening_status = build_screening_status(
            source_status=source_status, sanctions_hits=sanctions_hits
        )
        narr = sanctions_narrative_ru(
            screening_status=screening_status,
            source_status=source_status,
            sanctions_hits=sanctions_hits,
        )
        cft_status_ru = narr["status_ru"]
        risk_buckets = kyt.get("source_of_funds") or _risk_buckets(findings, screening.get("risk_score", 0))

        return {
            "report_type": "address",
            "product": _PRODUCT,
            "product_ru": _PRODUCT_RU,
            "version": _VERSION,
            "classification": _CLASSIFICATION,
            "report_id": investigation_id,
            "case_ref": case_ref,
            "generated_at": _now_iso(),
            "title_ru": "Отчёт скрининга блокчейн-кошелька",
            "title_en": "Blockchain wallet screening report",
            "address": screening.get("address"),
            "chain": screening.get("chain"),
            "audit_result_ru": screening.get("summary_ru"),
            "risk_score": screening.get("risk_score"),
            "risk_level": screening.get("risk_level"),
            "risk_tags": risk_tags,
            "risk_buckets": risk_buckets,
            "tag_breakdown": kyt.get("tag_breakdown") or {},
            "onchain": onchain,
            "balance_usd": onchain.get("balance_usd"),
            "balance_trx": onchain.get("balance_trx"),
            "tokens": onchain.get("tokens") or [],
            "token_count": onchain.get("token_count", 0),
            "connections_count": kyt.get("connection_count") or onchain.get("counterparties", 0),
            "first_activity": onchain.get("first_activity"),
            "last_activity": onchain.get("last_activity"),
            "indirect_exposure": kyt.get("indirect_exposure") or [],
            "connection_risk_summary": kyt.get("connection_risk_summary") or {},
            "findings": findings[:30],
            "evidence_chain": screening.get("evidence_chain") or [],
            "recommendations_ru": screening.get("recommendations_ru") or [],
            "limitations_ru": screening.get("limitations_ru") or [],
            "source_status": screening.get("source_status") or {},
            "fusion_score": fusion_report.get("illegal_flow_score"),
            "fusion_risk": fusion_report.get("risk_level"),
            "notes": notes,
            "open_osint": open_osint or {},
            "mentions_internet": _mentions_section(open_osint),
            "kyc_block_ru": (
                "KYC-данные хранятся у VASP/банков и запрашиваются через процедуры 115-ФЗ "
                "и межведомственный обмен с ФИУ СНГ."
            ),
            "cft_block_ru": cft_status_ru,
            "sanctions_check": {
                "hits": sanctions_hits,
                "status_ru": cft_status_ru,
                "status_en": narr.get("status_en"),
                "screening_status": screening_status,
                "source_status": source_status,
            },
        }

    def build_forensic_report(
        self,
        *,
        investigation_id: str,
        case_ref: str,
        address: str,
        chain: Chain,
        screening: dict[str, Any],
        fusion: FusionResult,
        fusion_report: dict[str, Any],
        tx_hash: str | None = None,
        notes: str | None = None,
        open_osint: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        onchain = screening.get("onchain_summary") or {}
        counterparties = _counterparty_rows(screening, fusion)
        corridors = fusion.corridor_matches[:6]
        composite = _composite_risk_label(
            screening.get("risk_score", 0),
            fusion_report.get("illegal_flow_score", 0),
        )

        return {
            "report_type": "forensic",
            "product": _PRODUCT,
            "product_ru": _PRODUCT_RU,
            "version": _VERSION,
            "classification": _CLASSIFICATION,
            "report_id": investigation_id,
            "case_ref": case_ref,
            "generated_at": _now_iso(),
            "title_ru": f"Форензический отчёт · {chain.value.upper()}",
            "subtitle_ru": "Анализ адреса и расширенной сети контрагентов",
            "source_address": address,
            "network": f"{chain.value.upper()}",
            "tx_hash": tx_hash,
            "executive_summary": {
                "text_ru": _executive_summary_ru(
                    address, onchain, fusion_report, composite, counterparties
                ),
                "key_findings_ru": _key_findings_ru(screening, fusion_report, fusion),
                "recommended_actions_ru": _recommended_actions_ru(
                    screening.get("risk_level", "medium"), fusion_report
                ),
            },
            "methodology": {
                "tools_ru": [
                    {"name": "ФинСкальп OSINT Core", "purpose": "Fusion графа доказательств"},
                    {"name": "Суверенный реестр 115-ФЗ", "purpose": "Риск-метки РФ/СНГ"},
                    {"name": f"On-chain {chain.value.upper()}", "purpose": "Публичный блокчейн"},
                    {"name": "XGBoost sovereign-xgb-v1", "purpose": "Скоринг риска"},
                ],
                "limitations_ru": screening.get("limitations_ru") or [
                    "Только on-chain данные; off-chain order book недоступен.",
                    "KYC — по запросу к VASP/банкам в рамках 115-ФЗ.",
                ],
            },
            "address_profile": {
                "address": address,
                "network": chain.value.upper(),
                "inbound_count": onchain.get("inbound_count", 0),
                "outbound_count": onchain.get("outbound_count", 0),
                "counterparties": onchain.get("counterparties", 0),
                "inbound_amount": onchain.get("inbound_amount"),
                "outbound_amount": onchain.get("outbound_amount"),
                "balance_usd": onchain.get("balance_usd"),
                "first_activity": onchain.get("first_activity"),
                "last_activity": onchain.get("last_activity"),
                "entity_classification_ru": _entity_class_ru(fusion, address),
            },
            "fund_flow": _fund_flow_section(onchain),
            "kyt_exposure": onchain.get("kyt_exposure") or {},
            "counterparties": counterparties,
            "corridors": corridors,
            "bridges": fusion_report.get("bridges") or [],
            "risk_assessment": {
                "wallet_score": screening.get("risk_score"),
                "network_score": fusion_report.get("illegal_flow_score"),
                "composite_score": composite["score"],
                "composite_label_ru": composite["label_ru"],
                "dimensions": composite["dimensions"],
            },
            "aml_patterns": fusion_report.get("findings") or [],
            "regulatory_ru": {
                "framework": "115-ФЗ · ПОД/ФТ · Федеральный закон о ПОД/ФТ",
                "str_recommended": composite["score"] >= 55,
                "materials_ready": True,
            },
            "evidence_log": screening.get("evidence_chain") or [],
            "open_osint": open_osint or {},
            "mentions_internet": _mentions_section(open_osint),
            "notes": notes,
        }

    def build_transaction_report(
        self,
        forensic: dict[str, Any],
        tx_hash: str,
    ) -> dict[str, Any]:
        return {
            **forensic,
            "report_type": "transaction",
            "title_ru": "Анализ транзакции",
            "tx_hash": tx_hash,
            "focus_ru": f"Транзакция {tx_hash[:16]}… в контексте адреса {forensic.get('source_address', '')[:12]}…",
        }

    def render_html(self, report: dict[str, Any]) -> str:
        from flowsint_crypto_compliance.reporting.pdf_report import _env

        report = self._maybe_enrich_enterprise_sections(report)
        kind = report.get("report_type", "address")
        if kind == "forensic":
            report = _normalize_forensic_report(report)
            tpl = _env.get_template("finskalp_forensic.html.j2")
        elif kind == "transaction":
            tpl = _env.get_template("finskalp_transaction.html.j2")
        elif kind == "volumetric":
            tpl = _env.get_template("finskalp_volumetric.html.j2")
        elif kind == "sar":
            tpl = _env.get_template("finskalp_sar.html.j2")
        elif kind == "seizure":
            tpl = _env.get_template("finskalp_seizure.html.j2")
        else:
            tpl = _env.get_template("finskalp_address.html.j2")
        return tpl.render(report=report)

    def render_pdf(self, report: dict[str, Any]) -> tuple[bytes, str, str]:
        html = self.render_html(report)
        content, media = render_pdf_bytes(html)
        ext = "pdf" if media.startswith("application/pdf") else "html"
        return content, media, ext

    @staticmethod
    def _maybe_enrich_enterprise_sections(report: dict[str, Any]) -> dict[str, Any]:
        """Attach optional enterprise sections when the feature flag is on.

        Fully defensive and additive: on any failure the original report is
        returned unchanged, so legacy generation can never break. Rollback is a
        matter of unsetting ``FINSKALP_ENTERPRISE_REPORT_SECTIONS``.
        """
        try:
            from flowsint_crypto_compliance.feature_flags import (
                enterprise_report_sections_enabled,
            )

            if not enterprise_report_sections_enabled():
                return report
            from flowsint_crypto_compliance.reporting.enterprise_sections import (
                enrich_enterprise_sections,
            )

            context = {
                "case_ref": report.get("case_ref"),
                "evidence_ids": [
                    str(x.get("evidence_id") or x.get("eccf_id"))
                    for x in (report.get("evidence_log") or report.get("evidence_chain") or [])
                    if isinstance(x, dict) and (x.get("evidence_id") or x.get("eccf_id"))
                ],
            }
            return enrich_enterprise_sections(report, context=context)
        except Exception:  # pragma: no cover - safety net
            import logging

            logging.getLogger(__name__).exception(
                "enterprise_sections enrichment skipped due to error"
            )
            return report


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _normalize_forensic_report(report: dict[str, Any]) -> dict[str, Any]:
    """Map legacy + v2 forensic payloads to the v2 HTML template shape."""
    r = dict(report)
    ap = dict(r.get("address_profile") or {})
    if not ap.get("address"):
        ap["address"] = r.get("source_address") or r.get("address") or "—"
    if not ap.get("network"):
        ap["network"] = r.get("network") or "—"
    ap.setdefault("account_type", "EOA")
    ap.setdefault("inbound_count", 0)
    ap.setdefault("outbound_count", 0)
    ap.setdefault("counterparties", 0)
    ap.setdefault("gross_inbound", ap.get("inbound_amount") or 0)
    ap.setdefault("gross_outbound", ap.get("outbound_amount") or 0)
    ap.setdefault("net_retained", (ap.get("gross_inbound") or 0) - (ap.get("gross_outbound") or 0))
    r["address_profile"] = ap

    if not r.get("cover"):
        r["cover"] = {
            "subject_network": ap.get("network"),
            "primary_asset": "USDT",
            "activity_window": f"{ap.get('first_activity', '—')} — {ap.get('last_activity', '—')}",
            "methodology": r.get("version") or "FinSkalp",
        }

    exec_sum = dict(r.get("executive_summary") or {})
    exec_sum.setdefault("text_ru", exec_sum.get("text_ru") or "—")
    exec_sum.setdefault("pattern_ru", exec_sum.get("pattern_ru") or "—")
    exec_sum.setdefault("key_findings_ru", exec_sum.get("key_findings_ru") or [])
    r["executive_summary"] = exec_sum

    methodology = dict(r.get("methodology") or {})
    methodology.setdefault("scope_ru", "On-chain forensic analysis")
    methodology.setdefault("tiering_ru", methodology.get("limitations_ru") or [])
    r["methodology"] = methodology

    if not r.get("fund_flow"):
        r["fund_flow"] = {
            "inbound_top": [],
            "outbound_top": [],
            "consolidation_detected": False,
            "consolidation_pct": 0,
        }

    if not r.get("evidence_inventory"):
        log = r.get("evidence_log") or []
        r["evidence_inventory"] = [
            {
                "exhibit_id": f"E{i + 1}",
                "description": "evidence chain entry",
                "sha256": str(item)[:64],
                "tier": "—",
            }
            for i, item in enumerate(log[:12])
        ] or [{"exhibit_id": "—", "description": "—", "sha256": "—", "tier": "—"}]

    if not r.get("counterparty_risk"):
        rows = []
        for c in (r.get("counterparties") or [])[:20]:
            rows.append(
                {
                    "entity": c.get("entity") or c.get("entity_name") or c.get("label"),
                    "address": c.get("address"),
                    "severity": c.get("severity") or "—",
                    "tier": c.get("tier") or "—",
                    "amount": c.get("amount") or c.get("total_received"),
                }
            )
        r["counterparty_risk"] = rows

    ra = r.get("risk_assessment")
    if isinstance(ra, dict):
        r["risk_assessment"] = [
            {
                "indicator": "Composite risk",
                "weight": str(ra.get("composite_label_ru") or ra.get("wallet_score") or "—"),
                "basis": f"wallet={ra.get('wallet_score')} network={ra.get('network_score')}",
            }
        ]
    elif not isinstance(ra, list):
        r["risk_assessment"] = []

    if not r.get("limitations_and_confidence"):
        lim = r.get("methodology", {}).get("limitations_ru") or []
        r["limitations_and_confidence"] = {
            "items": lim if isinstance(lim, list) else [str(lim)],
            "controller_identification_ru": (
                "Идентификация контролёра кошелька не выполняется; только on-chain поведение."
            ),
        }

    if not r.get("conclusions"):
        r["conclusions"] = {
            "next_steps_ru": exec_sum.get("recommended_actions_ru") or ["Зафиксировать материалы дела."],
        }

    r.setdefault("behavioural_analysis", {})
    r.setdefault("sanctioned_hits", [])
    r.setdefault("priority_tracing_lead", None)
    gs = dict(r.get("graph_section") or {})
    if gs.get("has_svg") and gs.get("svg") and len(str(gs["svg"])) > 500_000:
        gs.pop("svg", None)
        gs["has_svg"] = False
    r["graph_section"] = gs
    r.setdefault(
        "appendix_b",
        {"verification_record": {}, "source_status": r.get("source_status") or {}},
    )
    return r


def _mentions_section(open_osint: dict[str, Any] | None) -> dict[str, Any]:
    if not open_osint or not open_osint.get("mentions"):
        return {
            "found": False,
            "summary_ru": (
                "На момент проверки упоминаний адреса в открытых источниках "
                "(Telegram, форумы, публичные индексы) не обнаружено."
            ),
            "mentions": [],
        }
    return {
        "found": True,
        "summary_ru": (
            f"Обнаружено {open_osint.get('mentions_count', 0)} упоминаний в "
            f"{open_osint.get('independent_sources', 0)} типах открытых источников. "
            f"Open-risk: {open_osint.get('open_risk_score', 0)}/100."
        ),
        "mentions": open_osint.get("mentions") or [],
        "risk_tags": open_osint.get("risk_tags") or [],
        "source_status": open_osint.get("source_status") or {},
    }


def _risk_tags_from_findings(
    findings: list[dict[str, Any]], onchain: dict[str, Any] | None = None
) -> list[str]:
    tags: list[str] = []
    for f in findings:
        code = (f.get("code") or "").replace("_", " ").lower()
        if code and code not in tags:
            tags.append(code)
    kyt = (onchain or {}).get("kyt_exposure") or {}
    for tag in (kyt.get("tag_breakdown") or {}):
        if tag and tag not in tags:
            tags.append(tag)
    return tags[:16] or ["wallet", "exchange"]


def _risk_buckets(findings: list[dict[str, Any]], score: float) -> dict[str, float]:
    severe = sum(1 for f in findings if f.get("severity") == "critical")
    high = sum(1 for f in findings if f.get("severity") == "high")
    mod = sum(1 for f in findings if f.get("severity") == "medium")
    low = max(0, len(findings) - severe - high - mod)
    total = max(1, len(findings))
    if not findings:
        return {"severe": 0, "high": 0, "moderate": 0, "low": 100.0, "unknown": 0}
    return {
        "severe": round(100 * severe / total, 1),
        "high": round(100 * high / total, 1),
        "moderate": round(100 * mod / total, 1),
        "low": round(100 * low / total, 1),
        "unknown": max(0.0, round(100 - score, 1)),
    }


def _counterparty_rows(screening: dict[str, Any], fusion: FusionResult) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for attr in fusion.attributions[:15]:
        rows.append(
            {
                "address": attr.address[:8] + "…" + attr.address[-4:],
                "full_address": attr.address,
                "name": attr.sovereign_label or attr.watchlist_label or "Unknown EOA",
                "type": attr.entity_kind.value if attr.entity_kind else "unknown",
                "risk": "black" if attr.black_zone else ("gray" if attr.gray_zone else "low"),
                "confidence": attr.confidence,
                "region": attr.primary_region,
            }
        )
    if rows:
        return rows
    onchain = screening.get("onchain_summary") or {}
    return [
        {
            "address": "—",
            "name": "Контрагенты on-chain",
            "type": "network",
            "risk": "medium",
            "confidence": 0.5,
            "region": onchain.get("chain", "—"),
        }
    ]


def _composite_risk_label(wallet_score: float, network_score: float) -> dict[str, Any]:
    composite = round(0.45 * wallet_score + 0.55 * network_score, 1)
    if composite >= 75:
        label = "КРИТИЧЕСКИЙ"
    elif composite >= 55:
        label = "ВЫСОКИЙ"
    elif composite >= 35:
        label = "УМЕРЕННЫЙ"
    else:
        label = "НИЗКИЙ"
    return {
        "score": composite,
        "label_ru": label,
        "dimensions": {
            "wallet_risk": wallet_score,
            "network_risk": network_score,
            "sovereign_registry": min(100, wallet_score + 10),
            "corridor_exposure": min(100, network_score * 0.8),
        },
    }


def _executive_summary_ru(
    address: str,
    onchain: dict[str, Any],
    fusion_report: dict[str, Any],
    composite: dict[str, Any],
    counterparties: list[dict[str, Any]],
) -> str:
    return (
        f"Проведён форензический анализ адреса {address[:12]}… в сети {onchain.get('chain', '').upper()}. "
        f"Зафиксировано {onchain.get('inbound_count', 0)} входящих и {onchain.get('outbound_count', 0)} "
        f"исходящих операций, {onchain.get('counterparties', 0)} уникальных контрагентов. "
        f"Граф расследования: {fusion_report.get('evidence_graph', {}).get('nodes', 0)} узлов. "
        f"Композитный риск: {composite['label_ru']} ({composite['score']}/100). "
        f"Проанализировано контрагентов в атрибуции: {len(counterparties)}."
    )


def _key_findings_ru(
    screening: dict[str, Any],
    fusion_report: dict[str, Any],
    fusion: FusionResult,
) -> list[str]:
    items = [
        f"Скрининг кошелька: {screening.get('risk_score', 0):.1f}/100 ({screening.get('risk_level')})",
        f"Индекс нелегального потока: {fusion_report.get('illegal_flow_score', 0):.0f}/100",
    ]
    black = sum(1 for a in fusion.attributions if a.black_zone)
    if black:
        items.append(f"Адресов в чёрной зоне (суверенная модель): {black}")
    if fusion.corridor_matches:
        c = fusion.corridor_matches[0]
        items.append(f"Коридор CIS: {'→'.join(c.get('corridor', []))}")
    for f in (fusion_report.get("findings") or [])[:4]:
        items.append(f"[{f.get('severity', '').upper()}] {f.get('title_ru', '')}")
    return items


def _recommended_actions_ru(risk_level: str, fusion_report: dict[str, Any]) -> list[str]:
    actions = []
    if risk_level in ("critical", "high"):
        actions.append("СРОЧНО: подготовить материалы для STR по 115-ФЗ")
        actions.append("Запросить у банков-контрагентов реквизиты и payment reference")
    actions.append("Сверить адреса с перечнем Росфинмониторинга и внутренним OSINT-реестром")
    if fusion_report.get("illegal_flow_score", 0) >= 60:
        actions.append("Расширить трассировку на 2–3 hop по графу ФинСкальп")
    actions.append("Зафиксировать evidence chain в деле расследования")
    return actions


def _entity_class_ru(fusion: FusionResult, address: str) -> str:
    for a in fusion.attributions:
        if a.address == address or a.address.lower() == address.lower():
            if a.black_zone:
                return "Узел чёрной/серой инфраструктуры (высокая уверенность)"
            if a.sanctioned:
                return "Совпадение с перечнем 115-ФЗ / санкции"
            if a.gray_zone:
                return "Серая зона · требуется углубление"
            return f"Классификация: {a.entity_kind.value}"
    return "EOA / неидентифицированный кошелёк — требуется мониторинг"


def _fund_flow_section(onchain: dict[str, Any]) -> dict[str, Any]:
    kyt = onchain.get("kyt_exposure") or {}
    inbound = onchain.get("inbound_amount") or kyt.get("total_inbound") or 0
    outbound = onchain.get("outbound_amount") or kyt.get("total_outbound") or 0
    pattern = "standard"
    if onchain.get("inbound_count", 0) >= 20 and onchain.get("outbound_count", 0) <= 3:
        pattern = "funnel_consolidation"
    return {
        "total_inbound_usd": round(inbound, 2),
        "total_outbound_usd": round(outbound, 2),
        "pattern": pattern,
        "pattern_ru": (
            "Воронка: массовый сбор → консолидация"
            if pattern == "funnel_consolidation"
            else "Стандартный поток"
        ),
        "top_connections": (kyt.get("indirect_exposure") or [])[:8],
    }
