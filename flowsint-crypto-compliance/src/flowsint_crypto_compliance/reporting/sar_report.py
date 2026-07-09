"""
SAR / СПО — структурированное сообщение о подозрительной операции (115-ФЗ).

Агрегирует все артефакты расследования FinSkalp в единый регуляторный пакет.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class SarReportBuilder:
    """Сборка SAR из результатов полного цикла FinSkalp."""

    def build(
        self,
        *,
        investigation_id: str,
        case_ref: str,
        address: str,
        chain: str,
        screening: dict[str, Any],
        fusion_report: dict[str, Any],
        forensic_report: dict[str, Any] | None = None,
        open_osint: dict[str, Any] | None = None,
        subject_id: str | None = None,
        bank_name: str | None = None,
        bank_reference: str | None = None,
        amount: float | None = None,
        currency: str | None = None,
        tx_hash: str | None = None,
        notes: str | None = None,
        investigation_id_for_urls: str | None = None,
    ) -> dict[str, Any]:
        forensic = forensic_report or {}
        osint = open_osint or {}
        onchain = screening.get("onchain_summary") or {}
        attr = onchain.get("attribution") or {}
        kyt = onchain.get("kyt_exposure") or {}
        wallet_score = float(screening.get("risk_score") or 0)
        fusion_score = float(fusion_report.get("illegal_flow_score") or 0)
        composite_score = round(0.45 * wallet_score + 0.55 * fusion_score, 1)
        risk_level = screening.get("risk_level") or "medium"
        ap = forensic.get("address_profile") or {}

        suspicion_indicators = _suspicion_indicators(screening, fusion_report, osint, attr)
        evidence_sections = _evidence_sections(
            screening=screening,
            fusion_report=fusion_report,
            forensic=forensic,
            open_osint=osint,
            onchain=onchain,
            attr=attr,
        )
        decision = _decision_bundle(composite_score, risk_level, suspicion_indicators)
        inv = investigation_id_for_urls or investigation_id

        return {
            "report_type": "sar",
            "product": "FinSkalp",
            "product_ru": "ФинСкальп",
            "title_ru": "SAR · Сообщение о подозрительной операции · 115-ФЗ",
            "classification": "КОНФИДЕНЦИАЛЬНО · 115-ФЗ",
            "report_id": investigation_id,
            "case_ref": case_ref,
            "generated_at": _now(),
            "filing": {
                "message_type_ru": "Сообщение о подозрительной операции (СПО) / SAR",
                "recipient_ru": "Росфинмониторинг",
                "reporting_entity_ru": "ФинСкальп · операционный центр ПОД/ФТ",
                "legal_basis_ru": [
                    "Федеральный закон от 07.08.2001 № 115-ФЗ «О противодействии легализации "
                    "(отмыванию) доходов, полученных преступным путём, и финансированию терроризма»",
                    "ст. 6 — признаки подозрительных операций",
                    "ст. 7 — обязанности уполномоченных организаций",
                ],
            },
            "subject": {
                "subject_id": subject_id or "—",
                "address": address,
                "chain": chain.upper(),
                "entity_classification_ru": ap.get("entity_classification_ru")
                or "EOA / неидентифицированный кошелёк",
                "bank_name": bank_name,
                "bank_reference": bank_reference,
                "amount": f"{amount:,.0f} {currency}" if amount else None,
            },
            "operation": {
                "address": address,
                "chain": chain.upper(),
                "tx_hash": tx_hash,
                "inbound_count": onchain.get("inbound_count", 0),
                "outbound_count": onchain.get("outbound_count", 0),
                "counterparties": onchain.get("counterparties", 0),
                "balance_usd": onchain.get("balance_usd"),
                "inbound_amount": onchain.get("inbound_amount"),
                "outbound_amount": onchain.get("outbound_amount"),
                "activity_window": (
                    f"{onchain.get('first_activity', '—')} — {onchain.get('last_activity', '—')}"
                ),
                "connections_count": kyt.get("connection_count") or onchain.get("counterparties", 0),
            },
            "risk_profile": {
                "wallet_score": wallet_score,
                "fusion_score": fusion_score,
                "composite_score": composite_score,
                "composite_label_ru": _risk_label(composite_score),
                "risk_level": risk_level,
                "open_risk_score": osint.get("open_risk_score", 0),
                "graph_nodes": fusion_report.get("evidence_graph", {}).get("nodes", 0),
                "graph_edges": fusion_report.get("evidence_graph", {}).get("edges", 0),
            },
            "suspicion_indicators": suspicion_indicators,
            "narrative_ru": _narrative(
                address=address,
                chain=chain,
                screening=screening,
                fusion_report=fusion_report,
                forensic=forensic,
                osint=osint,
                composite_score=composite_score,
                suspicion_indicators=suspicion_indicators,
            ),
            "evidence_sections": evidence_sections,
            "executive_summary_ru": forensic.get("executive_summary", {}).get("text_ru")
            or screening.get("summary_ru")
            or "",
            "key_findings_ru": forensic.get("executive_summary", {}).get("key_findings_ru")
            or [],
            "decision": decision,
            "attachments_index": [
                {
                    "type": "sar",
                    "title_ru": "SAR · структурированный отчёт",
                    "url": f"/api/finskalp/report/{inv}/pdf?type=sar",
                },
                {
                    "type": "forensic",
                    "title_ru": "Форензика · полный отчёт",
                    "url": f"/api/finskalp/report/{inv}/pdf?type=forensic",
                },
                {
                    "type": "volumetric",
                    "title_ru": "Объёмный пакет доказательств",
                    "url": f"/api/finskalp/report/{inv}/pdf?type=volumetric",
                },
                {
                    "type": "address",
                    "title_ru": "Скрининг адреса",
                    "url": f"/api/finskalp/report/{inv}/pdf?type=address",
                },
            ],
            "analyst_notes": notes,
        }


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _risk_label(score: float) -> str:
    if score >= 75:
        return "КРИТИЧЕСКИЙ"
    if score >= 55:
        return "ВЫСОКИЙ"
    if score >= 35:
        return "УМЕРЕННЫЙ"
    return "НИЗКИЙ"


def _suspicion_indicators(
    screening: dict[str, Any],
    fusion_report: dict[str, Any],
    open_osint: dict[str, Any],
    attr: dict[str, Any],
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for sign in screening.get("legal_signs_ru") or []:
        items.append(
            {
                "article_ru": sign,
                "indicator_ru": sign,
                "confirmed": "да",
                "source": "115-ФЗ / скрининг",
            }
        )
    for f in (screening.get("findings") or [])[:8]:
        items.append(
            {
                "article_ru": f"Индикатор {f.get('code', '')}",
                "indicator_ru": f.get("title_ru", ""),
                "confirmed": "да" if f.get("severity") in ("critical", "high") else "частично",
                "source": "скрининг кошелька",
            }
        )
    for f in (fusion_report.get("findings") or [])[:6]:
        items.append(
            {
                "article_ru": f"AML · {f.get('code', '')}",
                "indicator_ru": f.get("title_ru", ""),
                "confirmed": "да" if f.get("severity") in ("critical", "high") else "частично",
                "source": "OSINT Fusion",
            }
        )
    for hit in (attr.get("sanctions_hits") or [])[:4]:
        items.append(
            {
                "article_ru": "ст. 6 115-ФЗ · санкции / перечни",
                "indicator_ru": hit.get("label") or hit.get("source") or "совпадение",
                "confirmed": "да",
                "source": hit.get("source", "sanctions"),
            }
        )
    if open_osint.get("mentions_count", 0) > 0:
        items.append(
            {
                "article_ru": "п. 1 ч. 2 ст. 6 115-ФЗ · ЦФА",
                "indicator_ru": (
                    f"Упоминания в открытых источниках: {open_osint.get('mentions_count', 0)}"
                ),
                "confirmed": "частично",
                "source": "Scalpel OSINT",
            }
        )
    return items


def _evidence_sections(
    *,
    screening: dict[str, Any],
    fusion_report: dict[str, Any],
    forensic: dict[str, Any],
    open_osint: dict[str, Any],
    onchain: dict[str, Any],
    attr: dict[str, Any],
) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []

    onchain_items = [
        f"Входящих: {onchain.get('inbound_count', 0)}, исходящих: {onchain.get('outbound_count', 0)}",
        f"Контрагентов: {onchain.get('counterparties', 0)}",
        f"Баланс USD: {onchain.get('balance_usd', '—')}",
        f"Окно активности: {onchain.get('first_activity', '—')} — {onchain.get('last_activity', '—')}",
    ]
    sections.append({"id": "onchain", "title_ru": "On-chain верификация", "items": onchain_items})

    screening_items = [
        f"Risk score: {screening.get('risk_score', 0)}/100 ({screening.get('risk_level', '—')})",
        f"Сводка: {screening.get('summary_ru', '—')}",
    ]
    screening_items.extend(
        f"[{f.get('severity', '').upper()}] {f.get('title_ru', '')}"
        for f in (screening.get("findings") or [])[:12]
    )
    sections.append({"id": "screening", "title_ru": "Скрининг · реестр 115-ФЗ", "items": screening_items})

    sanctions_items = [
        f"{h.get('source', 'sanctions')}: {h.get('label', h.get('address', '—'))}"
        for h in (attr.get("sanctions_hits") or [])
    ] or ["Совпадений с санкционными перечнями не обнаружено"]
    sections.append({"id": "sanctions", "title_ru": "Санкции / перечни", "items": sanctions_items})

    osint_items = [
        f"Сигналов: {open_osint.get('mentions_count', 0)}, "
        f"источников: {open_osint.get('independent_sources', 0)}, "
        f"open-risk: {open_osint.get('open_risk_score', 0)}/100",
    ]
    osint_items.extend(
        f"[{m.get('source_type', 'osint')}] {m.get('title_ru', '')}"
        for m in (open_osint.get("mentions") or [])[:15]
    )
    sections.append({"id": "osint", "title_ru": "Открытый OSINT · Scalpel", "items": osint_items})

    fusion_items = [
        f"Индекс нелегального потока: {fusion_report.get('illegal_flow_score', 0)}/100",
        f"Граф: {fusion_report.get('evidence_graph', {}).get('nodes', 0)} узлов, "
        f"{fusion_report.get('evidence_graph', {}).get('edges', 0)} рёбер",
    ]
    fusion_items.extend(
        f"[{f.get('severity', '').upper()}] {f.get('title_ru', '')}"
        for f in (fusion_report.get("findings") or [])[:12]
    )
    sections.append({"id": "fusion", "title_ru": "OSINT Fusion · AML", "items": fusion_items})

    attr_items = [
        f"{c.get('entity_name', c.get('label', '—'))} · {c.get('wallet_address', c.get('address', ''))[:16]}… "
        f"· conf {c.get('confidence', 0):.0%}"
        for c in (attr.get("connections") or [])[:12]
    ] or ["Атрибуция по суверенному реестру не выявила именованных сущностей"]
    sections.append({"id": "attribution", "title_ru": "Суверенная атрибуция", "items": attr_items})

    evidence_log = forensic.get("evidence_inventory") or forensic.get("evidence_log") or []
    graph_items = [
        str(e.get("description", e)) if isinstance(e, dict) else str(e)
        for e in evidence_log[:15]
    ] or ["Evidence chain зафиксирован в форензическом отчёте"]
    sections.append({"id": "evidence_chain", "title_ru": "Цепочка доказательств", "items": graph_items})

    return sections


def _decision_bundle(
    composite_score: float,
    risk_level: str,
    indicators: list[dict[str, str]],
) -> dict[str, Any]:
    confirmed = sum(1 for i in indicators if i.get("confirmed") == "да")
    if risk_level in ("critical", "high") or composite_score >= 55:
        return {
            "decision_ru": (
                "Направить сообщение о подозрительной операции (SAR/СПО) "
                "в Росфинмониторинг; инициировать межведомственный запрос"
            ),
            "basis_ru": (
                f"Композитный риск {composite_score}/100 ({_risk_label(composite_score)}). "
                f"Подтверждённых индикаторов: {confirmed}."
            ),
            "recommended_actions_ru": [
                "Направить SAR/СПО в Росфинмониторинг (115-ФЗ, ст. 7)",
                "Приложить форензический отчёт и объёмный пакет доказательств",
                "Запросить KYC/выписку у банка-контрагента",
                "Внести адреса в суверенный реестр повышенного риска",
                "Передать on-chain артефакты в оперативное заземление",
            ],
            "str_recommended": True,
        }
    if composite_score >= 25:
        return {
            "decision_ru": "Продолжить мониторинг; подготовить уточняющее SAR при новых сигналах",
            "basis_ru": (
                f"Частичное подтверждение признаков. Композитный риск {composite_score}/100."
            ),
            "recommended_actions_ru": [
                "Запросить расширенную выписку у банка",
                "Продлить on-chain мониторинг 30 суток",
                "Повторить Scalpel OSINT после обновления реестра",
            ],
            "str_recommended": False,
        }
    return {
        "decision_ru": "Закрыть с занесением в реестр наблюдения",
        "basis_ru": f"Недостаточно оснований для SAR. Композитный риск {composite_score}/100.",
        "recommended_actions_ru": [
            "Архивировать материалы проверки",
            "Оставить адрес на фоновом мониторинге",
        ],
        "str_recommended": False,
    }


def _narrative(
    *,
    address: str,
    chain: str,
    screening: dict[str, Any],
    fusion_report: dict[str, Any],
    forensic: dict[str, Any],
    osint: dict[str, Any],
    composite_score: float,
    suspicion_indicators: list[dict[str, str]],
) -> str:
    onchain = screening.get("onchain_summary") or {}
    confirmed = sum(1 for i in suspicion_indicators if i.get("confirmed") == "да")
    exec_text = forensic.get("executive_summary", {}).get("text_ru", "")
    return (
        f"По результатам расследования FinSkalp адрес {address} в сети {chain.upper()} "
        f"проанализирован в рамках 115-ФЗ. Зафиксировано {onchain.get('inbound_count', 0)} "
        f"входящих и {onchain.get('outbound_count', 0)} исходящих операций, "
        f"{onchain.get('counterparties', 0)} контрагентов. "
        f"Скрининг: {screening.get('risk_score', 0)}/100; fusion: "
        f"{fusion_report.get('illegal_flow_score', 0)}/100; композит: {composite_score}/100. "
        f"OSINT: {osint.get('mentions_count', 0)} сигналов в открытых источниках. "
        f"Подтверждённых признаков подозрительности: {confirmed}. "
        f"{exec_text}"
    ).strip()
