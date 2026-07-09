"""
Формирование отчётности по результатам проверки в рамках 115-ФЗ (ПОД/ФТ).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.demo.alert_registry import ScenarioAlertMeta, get_scenario_meta
from flowsint_crypto_compliance.detection.findings import IllegalFlowFinding

_report_seq = 0


def _next_report_id() -> str:
    global _report_seq
    _report_seq += 1
    dt = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"ОТЧ-115-{dt}-{_report_seq:04d}"


@dataclass
class FZ115CheckReport:
    """Справка по результатам проверки / анализа подозрительной операции."""

    report_id: str
    report_type_ru: str
    classification_ru: str
    legal_basis_ru: list[str]
    case_ref: str
    alert_code: str
    subject_category_ru: str
    typology_code: str
    typology_name_ru: str
    bank_name: str | None
    operation_amount: str | None
    suspicion_signs: list[dict[str, str]]
    investigation_summary_ru: str
    evidence_items: list[str]
    instruments_used: list[str]
    risk_level: str
    illegal_flow_score: float
    findings_summary_ru: list[str]
    decision_ru: str
    decision_basis_ru: str
    recommended_actions_ru: list[str]
    responsible_officer_ru: str
    generated_at: str
    executive_summary_ru: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "report_type_ru": self.report_type_ru,
            "classification_ru": self.classification_ru,
            "legal_basis_ru": self.legal_basis_ru,
            "case_ref": self.case_ref,
            "alert_code": self.alert_code,
            "subject_category_ru": self.subject_category_ru,
            "typology_code": self.typology_code,
            "typology_name_ru": self.typology_name_ru,
            "bank_name": self.bank_name,
            "operation_amount": self.operation_amount,
            "suspicion_signs": self.suspicion_signs,
            "investigation_summary_ru": self.investigation_summary_ru,
            "evidence_items": self.evidence_items,
            "instruments_used": self.instruments_used,
            "risk_level": self.risk_level,
            "illegal_flow_score": self.illegal_flow_score,
            "findings_summary_ru": self.findings_summary_ru,
            "decision_ru": self.decision_ru,
            "decision_basis_ru": self.decision_basis_ru,
            "recommended_actions_ru": self.recommended_actions_ru,
            "responsible_officer_ru": self.responsible_officer_ru,
            "generated_at": self.generated_at,
            "executive_summary_ru": self.executive_summary_ru,
        }


class FZ115ReportBuilder:
    """Генератор справок по 115-ФЗ на основе результатов OSINT-расследования."""

    def build(
        self,
        *,
        alert: dict[str, Any],
        investigation_report: dict[str, Any],
    ) -> FZ115CheckReport:
        scenario_id = alert["scenario_id"]
        meta = get_scenario_meta(scenario_id)
        findings = investigation_report.get("findings", [])
        risk = investigation_report.get("risk_level", "medium")
        score = float(investigation_report.get("illegal_flow_score", 0))

        suspicion_signs = [
            {"article_ru": sign, "confirmed": "да"}
            for sign in meta.legal_signs_ru
        ]
        for f in findings[:3]:
            suspicion_signs.append(
                {
                    "article_ru": f"Индикатор {f.get('code', '')}: {f.get('title_ru', '')}",
                    "confirmed": "да" if f.get("severity") in ("critical", "high") else "частично",
                }
            )

        decision, basis, actions = self._decision_bundle(risk, score, meta, alert)

        amount_str = None
        if alert.get("amount"):
            amount_str = f"{alert['amount']:,.0f} {alert.get('currency', 'RUB')}"

        evidence = self._collect_evidence(alert, investigation_report, findings)

        return FZ115CheckReport(
            report_id=_next_report_id(),
            report_type_ru=(
                "Справка по результатам проверки операции, "
                "в отношении которой поступило сообщение (115-ФЗ)"
            ),
            classification_ru="Для служебного пользования",
            legal_basis_ru=[
                "Федеральный закон от 07.08.2001 № 115-ФЗ «О противодействии легализации "
                "(отмыванию) доходов, полученных преступным путём, и финансированию терроризма»",
                "ст. 6 — признаки подозрительных операций",
                "ст. 7 — обязанности уполномоченных организаций и направление сообщений",
                "ст. 8 — обязанности и полномочия уполномоченного органа",
            ],
            case_ref=investigation_report.get("case_ref", alert.get("case_ref", "")),
            alert_code=alert.get("alert_code", alert.get("id", "")),
            subject_category_ru=meta.subject_category_ru,
            typology_code=meta.typology_code,
            typology_name_ru=meta.typology_name_ru,
            bank_name=alert.get("bank_name"),
            operation_amount=amount_str,
            suspicion_signs=suspicion_signs,
            investigation_summary_ru=investigation_report.get("executive_summary_ru", ""),
            evidence_items=evidence,
            instruments_used=alert.get("instruments", meta.instruments),
            risk_level=risk,
            illegal_flow_score=score,
            findings_summary_ru=[
                f"[{f.get('severity', '').upper()}] {f.get('title_ru', '')}"
                for f in findings
            ],
            decision_ru=decision,
            decision_basis_ru=basis,
            recommended_actions_ru=actions,
            responsible_officer_ru="Старший аналитик направления ЦФА / ПОД/ФТ",
            generated_at=datetime.now(timezone.utc).isoformat(),
            executive_summary_ru=self._executive(alert, meta, score, risk, decision),
        )

    def _decision_bundle(
        self,
        risk: str,
        score: float,
        meta: ScenarioAlertMeta,
        alert: dict[str, Any],
    ) -> tuple[str, str, list[str]]:
        if risk in ("critical", "high") or score >= 50:
            decision = (
                "Направить уточнённое сообщение о подозрительной операции "
                "в Росфинмониторинг; инициировать межведомственное взаимодействие"
            )
            basis = (
                f"Установлены признаки подозрительной операции ({meta.typology_code}), "
                f"индекс риска {score:.1f}/100. Достаточность доказательной базы: высокая."
            )
            actions = [
                "Направить материалы проверки в Росфинмониторинг (115-ФЗ, ст. 7)",
                "Запросить дополнительные сведения у {bank}".format(
                    bank=alert.get("bank_name") or "банка-участника"
                ),
                "Передать on-chain артефакты в контрольную закупку / оперативное заземление",
                "Внести адреса в суверенный реестр повышенного риска (115-ФЗ)",
                "Уведомить смежное подразделение по трансграничным коридорам (при наличии)",
            ]
        elif score >= 25:
            decision = "Продолжить мониторинг; запросить дополнительные сведения у банка"
            basis = (
                f"Признаки подозрительности частично подтверждены ({meta.typology_code}). "
                f"Индекс риска {score:.1f}/100 — требуется дообогащение."
            )
            actions = [
                "Запросить расширенную выписку и KYC-материалы у банка",
                "Продлить on-chain мониторинг на 30 суток (ИЦ-02)",
                "Повторная проверка после обновления суверенного реестра риск-меток",
            ]
        else:
            decision = "Закрыть проверку с занесением в реестр; мониторинг в фоновом режиме"
            basis = f"Недостаточно оснований для эскалации. Индекс риска {score:.1f}/100."
            actions = ["Архивировать материалы проверки", "Оставить адреса на наблюдении ИЦ-02"]
        return decision, basis, actions

    def _collect_evidence(
        self,
        alert: dict[str, Any],
        report: dict[str, Any],
        findings: list[dict[str, Any]],
    ) -> list[str]:
        items: list[str] = []
        if alert.get("hub_feed_id"):
            items.append(f"Сообщение банка (hub feed): {alert['hub_feed_id']}")
        if alert.get("pattern_indicators"):
            items.extend(f"Паттерн: {p}" for p in alert["pattern_indicators"][:4])
        metrics = report.get("metrics", {})
        if metrics.get("bank_crypto_links"):
            items.append(
                f"Склейка фиат↔крипто: {metrics['bank_crypto_links']} подтверждённых связей"
            )
        if metrics.get("registry_labels_applied"):
            items.append(f"Метки суверенного реестра (РФ/СНГ): {metrics['registry_labels_applied']}")
        if metrics.get("sanctioned_addresses"):
            items.append(f"Адреса в перечне 115-ФЗ / санкциях: {metrics['sanctioned_addresses']}")
        graph = report.get("evidence_graph", {})
        if graph.get("nodes"):
            items.append(
                f"Граф доказательств: {graph['nodes']} узлов, {graph['edges']} рёбер"
            )
        for f in findings[:5]:
            addrs = f.get("addresses") or []
            addr_part = f" ({addrs[0][:20]}…)" if addrs else ""
            items.append(f"{f.get('code', '')}: {f.get('title_ru', '')}{addr_part}")
        return items

    def _executive(
        self,
        alert: dict[str, Any],
        meta: ScenarioAlertMeta,
        score: float,
        risk: str,
        decision: str,
    ) -> str:
        return (
            f"По алерту {alert.get('alert_code', '')} ({meta.typology_code}) "
            f"проведена проверка в рамках 115-ФЗ. Индекс нелегального движения "
            f"ценностей: {score:.1f}/100 ({risk}). Решение: {decision}."
        )
