"""
Операционный центр регулятора: входящие STR, мониторинг паттернов, очередь расследований.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from flowsint_crypto_compliance.demo.alert_registry import (
    PATTERN_META,
    bank_alert_summary,
    bank_alert_title,
    format_bank_alert_code,
    format_monitor_alert_code,
    get_scenario_meta,
)
from flowsint_crypto_compliance.demo.combat_mode import combat_seed_address, is_combat_mode, resolve_crypto_from_scenario
from flowsint_crypto_compliance.demo.scenarios import SCENARIOS, DemoScenario, get_scenario
from flowsint_crypto_compliance.services.case_workflow import (
    DEFAULT_SLA_HOURS,
    WORKFLOW_STATUSES,
    can_transition,
    is_sla_breached,
    sla_due_at,
)

from flowsint_types.fiat_crypto import Chain
AlertStatus = Literal["new", "triaging", "investigating", "completed"]
AlertPriority = Literal["critical", "high", "medium", "low"]
WorkflowStatus = Literal[
    "new", "triage", "investigating", "pending_filing", "filed", "archived"
]

WORKFLOW_LABELS_RU: dict[str, str] = {
    "new": "Новое",
    "triage": "Триаж",
    "investigating": "Расследование",
    "pending_filing": "К подаче",
    "filed": "Подано",
    "archived": "Архив",
}

DEMO_ASSIGNEES = (
    "Аналитик Иванова",
    "Старший аналитик Петров",
    "Офицер комплаенса Сидорова",
    "Администратор системы",
)


@dataclass
class PatternRule:
    id: str
    title_ru: str
    description_ru: str
    scenario_id: str
    priority: AlertPriority
    indicators_ru: list[str]


PATTERN_RULES: list[PatternRule] = [
    PatternRule(
        id="hub_fanout_anomaly",
        title_ru=PATTERN_META["hub_fanout_anomaly"]["official_title_ru"],
        description_ru=(
            "Мониторинг on-chain (ИЦ-02): кошелёк с >50 входящих за 24ч и массовым "
            "распределением на mixer/OTC — типичный серый агрегатор СБП→крипто."
        ),
        scenario_id="sbp_gray_hub",
        priority="critical",
        indicators_ru=[
            "fan-in: 127 контрагентов за 24ч",
            "fan-out: 89 исходящих за 6ч",
            "корреляция с СБП-референсом банка (115-ФЗ)",
            "реестр 115-ФЗ: категория mixer (Росфинмониторинг)",
        ],
    ),
    PatternRule(
        id="cis_corridor_ru_kz",
        title_ru=PATTERN_META["cis_corridor_ru_kz"]["official_title_ru"],
        description_ru=(
            "Эвристика транзитного потока (ИЦ-06): OTC РФ → цепочка промежуточных "
            "кошельков → депозит на локальную площадку KZ."
        ),
        scenario_id="cis_transit_kz",
        priority="high",
        indicators_ru=[
            "OTC Telegram — контрольная закупка (ИЦ-03)",
            "≥3 транзитных hop на TRON",
            "выход: KZ_Local_Exchange",
            "коридор RU→KZ→TR",
        ],
    ),
    PatternRule(
        id="p2p_offshore_72h",
        title_ru=PATTERN_META["p2p_offshore_72h"]["official_title_ru"],
        description_ru=(
            "Корреляция STR банка + контрольная P2P + выход на адрес, "
            "размеченный суверенным реестром как офшорный CEX-вывод (ИЦ-05)."
        ),
        scenario_id="p2p_rub_offshore",
        priority="high",
        indicators_ru=[
            "STR > 2 000 000 ₽",
            "hub TRU_HUB_MSK (серая зона)",
            "реестр: офшорный CEX-вывод (confidence 0.82)",
            "окно корреляции: 72ч",
        ],
    ),
    PatternRule(
        id="layering_offshore_do",
        title_ru=PATTERN_META["layering_offshore_do"]["official_title_ru"],
        description_ru=(
            "P2P в РФ, структурное размывание на TRON (ИЦ-04), депозит на "
            "лицензированную площадку в юрисдiction DO (ИЦ-06)."
        ),
        scenario_id="cross_border_do",
        priority="high",
        indicators_ru=[
            "СПО: p2p_suspicion (Тинькофф)",
            "≥4 hop layering на TRON",
            "регион выхода: DO (офшор)",
            "лицензированный VASP — DO_Local_CEX",
        ],
    ),
]


@dataclass
class ComplianceAlert:
    id: str
    alert_code: str
    source: AlertSource
    status: AlertStatus
    priority: AlertPriority
    title_ru: str
    official_title_ru: str
    summary_ru: str
    scenario_id: str
    typology_code: str
    typology_name_ru: str
    legal_signs_ru: list[str]
    instruments: list[str]
    received_at: str
    bank_name: str | None = None
    amount: float | None = None
    currency: str | None = None
    region: str = "RU"
    pattern_id: str | None = None
    pattern_indicators: list[str] = field(default_factory=list)
    case_ref: str | None = None
    hub_feed_id: str | None = None
    subject_category_ru: str | None = None
    report: dict[str, Any] | None = None
    fz115_report: dict[str, Any] | None = None
    investigation_steps: list[dict[str, Any]] = field(default_factory=list)
    workflow_status: WorkflowStatus = "new"
    assignee: str | None = None
    due_at: str | None = None
    sla_hours: int = 72
    sla_breached: bool = False
    comments: list[dict[str, Any]] = field(default_factory=list)
    evidence_graph: dict[str, Any] | None = None
    crypto_address: str | None = None
    crypto_chain: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "alert_code": self.alert_code,
            "source": self.source,
            "source_label_ru": _source_label(self.source),
            "status": self.status,
            "status_label_ru": _status_label(self.status),
            "priority": self.priority,
            "title_ru": self.title_ru,
            "official_title_ru": self.official_title_ru,
            "summary_ru": self.summary_ru,
            "scenario_id": self.scenario_id,
            "typology_code": self.typology_code,
            "typology_name_ru": self.typology_name_ru,
            "legal_signs_ru": self.legal_signs_ru,
            "instruments": self.instruments,
            "received_at": self.received_at,
            "bank_name": self.bank_name,
            "amount": self.amount,
            "currency": self.currency,
            "region": self.region,
            "pattern_id": self.pattern_id,
            "pattern_indicators": self.pattern_indicators,
            "case_ref": self.case_ref,
            "hub_feed_id": self.hub_feed_id,
            "subject_category_ru": self.subject_category_ru,
            "has_report": self.report is not None,
            "has_fz115_report": self.fz115_report is not None,
            "report": self.report,
            "fz115_report": self.fz115_report,
            "investigation_steps": self.investigation_steps,
            "workflow_status": self.workflow_status,
            "workflow_label_ru": WORKFLOW_LABELS_RU.get(self.workflow_status, self.workflow_status),
            "assignee": self.assignee,
            "due_at": self.due_at,
            "sla_hours": self.sla_hours,
            "sla_breached": self._sla_breached(),
            "comments": self.comments,
            "has_graph": self.evidence_graph is not None,
            "evidence_graph": self.evidence_graph,
            "crypto_address": self.crypto_address,
            "crypto_chain": self.crypto_chain,
        }

    def _sla_breached(self) -> bool:
        if self.sla_breached:
            return True
        if not self.due_at:
            return False
        from datetime import datetime, timezone

        try:
            due = datetime.fromisoformat(self.due_at.replace("Z", "+00:00"))
        except ValueError:
            return False
        return is_sla_breached(due, self.workflow_status)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _publish_case_event(event_type: str, **fields: Any) -> None:
    try:
        from flowsint_crypto_compliance.infrastructure.compliance_events import get_event_bus

        text_ru = fields.pop("text_ru", None)
        severity = str(fields.pop("severity", "info"))
        get_event_bus().publish(
            event_type,
            payload=fields,
            severity=severity,
            text_ru=text_ru,
            correlation_id=fields.get("case_ref") or fields.get("alert_id"),
        )
    except Exception:
        pass


def _source_label(source: AlertSource) -> str:
    return {
        "bank_hub": "Хаб банковских сообщений (115-ФЗ / ИЦ-01)",
        "pattern_monitor": "Монитор паттернов (ИЦ-02)",
        "regulator_request": "Запрос уполномоченного органа",
    }[source]


def _status_label(status: AlertStatus) -> str:
    return {
        "new": "Новый",
        "triaging": "Первичная обработка",
        "investigating": "Расследование",
        "completed": "Проверка завершена",
    }[status]


def _alert_from_live_str(
    *,
    crypto_address: str,
    crypto_chain: str | None = None,
    scenario_id: str | None = None,
    bank_name: str = "Участник банковского хаба",
    amount: float | None = None,
) -> ComplianceAlert:
    from flowsint_crypto_compliance.demo.alert_registry import SCENARIO_META
    from flowsint_crypto_compliance.services.wallet_screening import infer_chain

    meta = SCENARIO_META.get(scenario_id or "p2p_rub_offshore")
    if not meta:
        meta = next(iter(SCENARIO_META.values()))
    chain = Chain(str(crypto_chain).lower()) if crypto_chain else infer_chain(crypto_address)
    alert = ComplianceAlert(
        id=f"alert-{uuid.uuid4().hex[:10]}",
        alert_code=f"STR-LIVE-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
        source="bank_hub",
        status="new",
        priority="high",
        title_ru=f"СОО · {bank_name} · {crypto_address[:12]}…",
        official_title_ru=meta.official_title_ru,
        summary_ru=f"Live STR · {chain.value.upper()} · {crypto_address}",
        scenario_id=meta.scenario_id,
        typology_code=meta.typology_code,
        typology_name_ru=meta.typology_name_ru,
        legal_signs_ru=list(meta.legal_signs_ru),
        instruments=list(meta.instruments),
        received_at=_now_iso(),
        bank_name=bank_name,
        amount=amount,
        currency="RUB",
        region="RU",
        case_ref=f"{meta.case_series}-{uuid.uuid4().hex[:6].upper()}",
        hub_feed_id=f"STR-LIVE-{uuid.uuid4().hex[:8]}",
        subject_category_ru=meta.subject_category_ru,
        crypto_address=crypto_address,
        crypto_chain=chain.value,
    )
    return alert


def _attach_crypto_target(alert: ComplianceAlert, *, override_address: str | None = None, override_chain: str | None = None) -> None:
    if override_address:
        alert.crypto_address = override_address.strip()
        alert.crypto_chain = (override_chain or "").strip().lower() or None
        return
    if alert.crypto_address:
        return
    seed = combat_seed_address()
    if seed:
        alert.crypto_address, chain = seed
        alert.crypto_chain = chain.value
        return
    if is_combat_mode():
        return
    addr, chain = resolve_crypto_from_scenario(alert.scenario_id)
    if addr:
        alert.crypto_address = addr
        alert.crypto_chain = chain.value if chain else None


def _alert_from_bank_scenario(
    scenario: DemoScenario,
    *,
    feed_index: int = 0,
    crypto_address: str | None = None,
    crypto_chain: str | None = None,
) -> ComplianceAlert:
    feed = scenario.bank_feeds[feed_index]
    meta = get_scenario_meta(scenario.id)
    priority: AlertPriority = "high"
    if feed.amount and feed.amount >= 2_000_000:
        priority = "critical"
    elif feed.amount and feed.amount < 600_000:
        priority = "medium"

    return ComplianceAlert(
        id=f"alert-{uuid.uuid4().hex[:10]}",
        alert_code=format_bank_alert_code(feed),
        source="bank_hub",
        status="new",
        priority=priority,
        title_ru=bank_alert_title(feed),
        official_title_ru=meta.official_title_ru,
        summary_ru=bank_alert_summary(feed, meta),
        scenario_id=scenario.id,
        typology_code=meta.typology_code,
        typology_name_ru=meta.typology_name_ru,
        legal_signs_ru=list(meta.legal_signs_ru),
        instruments=list(meta.instruments),
        received_at=_now_iso(),
        bank_name=feed.bank_name,
        amount=feed.amount,
        currency=feed.currency,
        region=feed.region or "RU",
        case_ref=scenario.case_ref,
        hub_feed_id=feed.feed_id,
        subject_category_ru=meta.subject_category_ru,
    )
    _attach_crypto_target(alert, override_address=crypto_address, override_chain=crypto_chain)
    return alert


def _alert_from_pattern(rule: PatternRule) -> ComplianceAlert:
    scenario = get_scenario(rule.scenario_id)
    meta = get_scenario_meta(rule.scenario_id)
    feed = scenario.bank_feeds[0] if scenario.bank_feeds else None
    pat = PATTERN_META.get(rule.id, {})
    alert = ComplianceAlert(
        id=f"alert-{uuid.uuid4().hex[:10]}",
        alert_code=format_monitor_alert_code(rule.id),
        source="pattern_monitor",
        status="new",
        priority=rule.priority,
        title_ru=rule.title_ru,
        official_title_ru=pat.get("official_title_ru", rule.title_ru),
        summary_ru=rule.description_ru,
        scenario_id=rule.scenario_id,
        typology_code=meta.typology_code,
        typology_name_ru=meta.typology_name_ru,
        legal_signs_ru=list(meta.legal_signs_ru),
        instruments=list(meta.instruments),
        received_at=_now_iso(),
        bank_name=feed.bank_name if feed else None,
        amount=feed.amount if feed else None,
        currency=feed.currency if feed else "RUB",
        region=feed.region if feed else "RU",
        pattern_id=rule.id,
        pattern_indicators=list(rule.indicators_ru),
        case_ref=scenario.case_ref,
        subject_category_ru=meta.subject_category_ru,
    )
    _attach_crypto_target(alert)
    return alert


class OperationsCenter:
    """Боевой контур: очередь алертов, приём STR, сканер паттернов, реестр отчётов."""

    def __init__(self) -> None:
        self._alerts: dict[str, ComplianceAlert] = {}
        self._lock = asyncio.Lock()
        self._pattern_seen: set[str] = set()
        self._live_kyt_seen: set[str] = set()
        self._bank_seen: set[str] = set()
        self._seed_working_queue()

    def _seed_working_queue(self) -> None:
        if is_combat_mode():
            return
        self._seed_default_alerts()

    def _seed_default_alerts(self) -> None:
        if self._alerts:
            return
        incoming = [
            _alert_from_bank_scenario(get_scenario("p2p_rub_offshore")),
            _alert_from_pattern(PATTERN_RULES[0]),
        ]
        incoming[0].workflow_status = "triage"
        incoming[0].assignee = DEMO_ASSIGNEES[0]
        incoming[0].due_at = sla_due_at("triage").isoformat() if sla_due_at("triage") else None
        incoming[0].sla_hours = 48
        incoming[0].comments = [
            {
                "id": "c-seed-1",
                "author": DEMO_ASSIGNEES[0],
                "text_ru": "STR от банка получен, назначен первичный триаж.",
                "created_at": _now_iso(),
            }
        ]
        for alert in incoming:
            _attach_crypto_target(alert)
            self._alerts[alert.id] = alert
            if alert.pattern_id:
                self._pattern_seen.add(alert.pattern_id)
            if alert.hub_feed_id:
                self._bank_seen.add(alert.hub_feed_id)

    async def bootstrap_live_queue(self) -> list[dict[str, Any]]:
        """Combat stand: populate inbox + feed from live watchlist on startup."""
        if not is_combat_mode():
            return []
        created: list[dict[str, Any]] = []
        seed = combat_seed_address()
        if seed:
            addr, chain = seed
            has_seed = any(
                (a.crypto_address or "").lower() == addr.lower()
                for a in self._alerts.values()
            )
            if not has_seed:
                try:
                    created.append(
                        await self.receive_bank_str(
                            crypto_address=addr,
                            crypto_chain=chain.value,
                        )
                    )
                except Exception:
                    pass
        found = await self.run_pattern_scan()
        created.extend(found)
        return created

    async def workflow_stats(self) -> dict[str, Any]:
        async with self._lock:
            items = list(self._alerts.values())
        counts = {status: 0 for status in WORKFLOW_STATUSES}
        for alert in items:
            ws = alert.workflow_status
            if ws in counts:
                counts[ws] += 1
        counts["filed_mtd"] = counts.get("filed", 0)
        return {
            "pipeline": counts,
            "total": len(items),
            "sla_breached": sum(1 for a in items if a._sla_breached()),
            "assignees": list(DEMO_ASSIGNEES),
        }

    async def transition_workflow(
        self,
        alert_id: str,
        *,
        target: WorkflowStatus,
        assignee: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        async with self._lock:
            alert = self._alerts.get(alert_id)
            if not alert:
                raise KeyError(f"Unknown alert: {alert_id}")
            current = alert.workflow_status
            if not can_transition(current, target):
                raise ValueError(f"Transition {current} → {target} not allowed")
            alert.workflow_status = target
            if assignee:
                alert.assignee = assignee
            due = sla_due_at(target)
            alert.due_at = due.isoformat() if due else None
            alert.sla_hours = DEFAULT_SLA_HOURS.get(target, 72)
            alert.sla_breached = False
            if target == "investigating":
                alert.status = "investigating"
            if target in ("filed", "archived"):
                alert.status = "completed"
            if note:
                alert.comments.append(
                    {
                        "id": f"c-{uuid.uuid4().hex[:8]}",
                        "author": assignee or alert.assignee or DEMO_ASSIGNEES[0],
                        "text_ru": note,
                        "created_at": _now_iso(),
                    }
                )
            if target == "filed":
                alert.comments.append(
                    {
                        "id": f"c-{uuid.uuid4().hex[:8]}",
                        "author": assignee or alert.assignee or DEMO_ASSIGNEES[2],
                        "text_ru": "Материалы переданы в реестр 115-ФЗ · filing подтверждён.",
                        "created_at": _now_iso(),
                    }
                )
        return alert.to_dict()

    async def add_comment(
        self,
        alert_id: str,
        *,
        text: str,
        author: str | None = None,
    ) -> dict[str, Any]:
        async with self._lock:
            alert = self._alerts.get(alert_id)
            if not alert:
                raise KeyError(f"Unknown alert: {alert_id}")
            alert.comments.append(
                {
                    "id": f"c-{uuid.uuid4().hex[:8]}",
                    "author": author or alert.assignee or DEMO_ASSIGNEES[0],
                    "text_ru": text.strip(),
                    "created_at": _now_iso(),
                }
            )
        return alert.to_dict()

    async def list_inbox(
        self,
        *,
        status: AlertStatus | None = None,
    ) -> list[dict[str, Any]]:
        async with self._lock:
            if not self._alerts:
                self._seed_default_alerts()
            items = list(self._alerts.values())
        items.sort(key=lambda a: a.received_at, reverse=True)
        if status:
            items = [a for a in items if a.status == status]
        return [a.to_dict() for a in items]

    async def list_reports(self) -> list[dict[str, Any]]:
        async with self._lock:
            items = [a for a in self._alerts.values() if a.fz115_report]
        items.sort(key=lambda a: a.received_at, reverse=True)
        return [
            {
                "alert_id": a.id,
                "alert_code": a.alert_code,
                "case_ref": a.case_ref,
                "report_id": a.fz115_report["report_id"] if a.fz115_report else None,
                "typology_code": a.typology_code,
                "risk_level": a.report.get("risk_level") if a.report else None,
                "generated_at": a.fz115_report.get("generated_at") if a.fz115_report else None,
                "decision_ru": a.fz115_report.get("decision_ru") if a.fz115_report else None,
            }
            for a in items
        ]

    async def get_alert(self, alert_id: str) -> dict[str, Any]:
        async with self._lock:
            alert = self._alerts.get(alert_id)
        if not alert:
            raise KeyError(f"Unknown alert: {alert_id}")
        return alert.to_dict()

    async def receive_bank_str(
        self,
        scenario_id: str | None = None,
        *,
        crypto_address: str | None = None,
        crypto_chain: str | None = None,
    ) -> dict[str, Any]:
        from flowsint_crypto_compliance.demo.live_ops_metrics import get_live_ops_metrics
        from flowsint_crypto_compliance.osint_core.multihop_fusion import is_live_address
        from flowsint_crypto_compliance.services.wallet_screening import infer_chain

        if is_combat_mode():
            addr = (crypto_address or "").strip()
            if not addr:
                seed = combat_seed_address()
                if seed:
                    addr, chain = seed
                    crypto_chain = crypto_chain or chain.value
                else:
                    raise ValueError(
                        "Live STR: укажите crypto_address или FINSKALP_COMBAT_SEED_ADDRESS"
                    )
            chain = infer_chain(addr)
            if crypto_chain:
                chain = Chain(str(crypto_chain).lower())
            if not is_live_address(addr, chain.value):
                raise ValueError(f"Адрес не live on-chain: {addr}")
            alert = _alert_from_live_str(
                crypto_address=addr,
                crypto_chain=chain.value,
                scenario_id=scenario_id,
            )
            async with self._lock:
                self._alerts[alert.id] = alert
            get_live_ops_metrics().record_str()
            payload = alert.to_dict()
            _publish_case_event(
                "case_new",
                alert_code=payload["alert_code"],
                alert_id=payload["id"],
                case_ref=payload.get("case_ref"),
                text_ru=f"Live СОО · {payload['alert_code']} · {addr[:12]}…",
                severity=payload.get("priority", "high"),
            )
            return payload

        async with self._lock:
            candidates = [
                sid
                for sid, sc in SCENARIOS.items()
                if sc.bank_feeds and sc.bank_feeds[0].feed_id not in self._bank_seen
            ]
            sid = scenario_id if scenario_id in candidates else None
            if sid is None and candidates:
                sid = candidates[0]
            if sid is None:
                sid = scenario_id or "p2p_rub_offshore"
            scenario = get_scenario(sid)
            alert = _alert_from_bank_scenario(
                scenario,
                crypto_address=crypto_address,
                crypto_chain=crypto_chain,
            )
            if alert.hub_feed_id:
                self._bank_seen.add(alert.hub_feed_id)
            self._alerts[alert.id] = alert
        payload = alert.to_dict()
        _publish_case_event(
            "case_new",
            alert_code=payload["alert_code"],
            alert_id=payload["id"],
            case_ref=payload.get("case_ref"),
            text_ru=f"Новое СОО · {payload['alert_code']} · {payload.get('bank_name') or 'KYT'}",
            severity=payload.get("priority", "high"),
        )
        return payload

    async def run_pattern_scan(self) -> list[dict[str, Any]]:
        if is_combat_mode():
            from flowsint_crypto_compliance.demo.live_kyt_scanner import run_live_kyt_scan

            found = await run_live_kyt_scan(seen=self._live_kyt_seen)
            async with self._lock:
                for alert in found:
                    self._alerts[alert.id] = alert
            for alert in found:
                payload = alert.to_dict()
                _publish_case_event(
                    "case_new",
                    alert_code=payload["alert_code"],
                    alert_id=payload["id"],
                    case_ref=payload.get("case_ref"),
                    text_ru=f"Live KYT · {payload['alert_code']} · риск on-chain",
                    severity=payload.get("priority", "high"),
                )
            return [a.to_dict() for a in found]

        found: list[ComplianceAlert] = []
        async with self._lock:
            for rule in PATTERN_RULES:
                if rule.id in self._pattern_seen:
                    continue
                alert = _alert_from_pattern(rule)
                self._pattern_seen.add(rule.id)
                self._alerts[alert.id] = alert
                found.append(alert)
        for alert in found:
            payload = alert.to_dict()
            _publish_case_event(
                "case_new",
                alert_code=payload["alert_code"],
                alert_id=payload["id"],
                case_ref=payload.get("case_ref"),
                text_ru=f"KYT-алерт · {payload['alert_code']} · {payload.get('title_ru', '')[:60]}",
                severity=payload.get("priority", "high"),
            )
        return [a.to_dict() for a in found]

    async def update_alert(
        self,
        alert_id: str,
        *,
        status: AlertStatus | None = None,
        report: dict[str, Any] | None = None,
        fz115_report: dict[str, Any] | None = None,
        steps: list[dict[str, Any]] | None = None,
        evidence_graph: dict[str, Any] | None = None,
        workflow_status: WorkflowStatus | None = None,
    ) -> None:
        async with self._lock:
            alert = self._alerts.get(alert_id)
            if not alert:
                raise KeyError(f"Unknown alert: {alert_id}")
            if status:
                alert.status = status
            if report is not None:
                alert.report = report
                graph = report.get("live_fusion") or report.get("graph_viz") or {}
                alt = report.get("graph_viz") if graph is report.get("live_fusion") else report.get("live_fusion")
                if alt and len(alt.get("edges") or []) > len(graph.get("edges") or []):
                    graph = alt
                if graph.get("nodes"):
                    alert.evidence_graph = graph
            if fz115_report is not None:
                alert.fz115_report = fz115_report
            if steps is not None:
                alert.investigation_steps = steps
            if evidence_graph is not None:
                alert.evidence_graph = evidence_graph
            if workflow_status:
                alert.workflow_status = workflow_status
                due = sla_due_at(workflow_status)
                alert.due_at = due.isoformat() if due else None
                alert.sla_hours = DEFAULT_SLA_HOURS.get(workflow_status, 72)

    async def stats(self) -> dict[str, int]:
        async with self._lock:
            items = list(self._alerts.values())
        return {
            "total": len(items),
            "new": sum(1 for a in items if a.status == "new"),
            "investigating": sum(1 for a in items if a.status == "investigating"),
            "completed": sum(1 for a in items if a.status == "completed"),
            "critical": sum(
                1 for a in items if a.priority == "critical" and a.status != "completed"
            ),
            "reports_fz115": sum(1 for a in items if a.fz115_report),
        }

    def list_patterns(self) -> list[dict[str, Any]]:
        return [
            {
                "id": r.id,
                "code": PATTERN_META.get(r.id, {}).get("code", r.id),
                "title_ru": r.title_ru,
                "description_ru": r.description_ru,
                "priority": r.priority,
                "scenario_id": r.scenario_id,
                "typology_code": get_scenario_meta(r.scenario_id).typology_code,
                "already_detected": r.id in self._pattern_seen,
            }
            for r in PATTERN_RULES
        ]
