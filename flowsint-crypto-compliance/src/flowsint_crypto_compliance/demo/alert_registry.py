"""
Реестр наименований алертов, типологий и правовых оснований (115-ФЗ / ПОД/ФТ).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from flowsint_types.fiat_crypto import BankRegulatorFeed

# Типы сообщений банка → официальное наименование
BANK_ALERT_TYPE_LABELS: dict[str, str] = {
    "STR": "Сообщение о подозрительной операции (СПО)",
    "crypto_suspicion": "СПО: операции с цифровыми финансовыми активами",
    "cross_border": "СПО: трансграничный перевод с признаками обхода",
    "p2p_suspicion": "СПО: P2P-операции / обналичивание через цифровые активы",
}


@dataclass(frozen=True)
class ScenarioAlertMeta:
    scenario_id: str
    official_title_ru: str
    typology_code: str
    typology_name_ru: str
    legal_signs_ru: list[str]
    instruments: list[str]
    subject_category_ru: str
    case_series: str


SCENARIO_META: dict[str, ScenarioAlertMeta] = {
    "p2p_rub_offshore": ScenarioAlertMeta(
        scenario_id="p2p_rub_offshore",
        official_title_ru=(
            "СПО: обналичивание/конвертация через P2P-канал с выводом "
            "на иностранную централизованную биржу (CEX)"
        ),
        typology_code="ПФТ-ЦФА-03",
        typology_name_ru="P2P → OTC hub → офшорный CEX",
        legal_signs_ru=[
            "п. 1 ч. 2 ст. 6 115-ФЗ — операции с цифровыми финансовыми активами",
            "п. 2 ч. 2 ст. 6 115-ФЗ — дробление / структурирование суммы",
            "п. 5 ч. 2 ст. 6 115-ФЗ — операции с участием офшорных юрисдикций",
        ],
        instruments=["ИЦ-01", "ИЦ-03", "ИЦ-05", "ИЦ-07", "ИЦ-08"],
        subject_category_ru="Физическое лицо — P2P-контрагент",
        case_series="КД-2026",
    ),
    "cis_transit_kz": ScenarioAlertMeta(
        scenario_id="cis_transit_kz",
        official_title_ru=(
            "СПО: транзитный перевод через цепочку криптоактивов "
            "с выходом на площадку Республики Казахстан"
        ),
        typology_code="ПФТ-ТР-02",
        typology_name_ru="Транзитный коридор РФ → KZ → TR",
        legal_signs_ru=[
            "п. 3 ч. 2 ст. 6 115-ФЗ — трансграничное перемещение ценностей",
            "п. 1 ч. 2 ст. 6 115-ФЗ — операции с ЦФА без экономического смысла",
            "п. 4 ч. 2 ст. 6 115-ФЗ — использование посредников (OTC)",
        ],
        instruments=["ИЦ-01", "ИЦ-02", "ИЦ-04", "ИЦ-06", "ИЦ-07", "ИЦ-08"],
        subject_category_ru="Физическое лицо — получатель перевода",
        case_series="КД-2026",
    ),
    "cross_border_do": ScenarioAlertMeta(
        scenario_id="cross_border_do",
        official_title_ru=(
            "СПО: layering на блокчейне TRON с выводом на VASP "
            "в юрисдiction Доминиканской Республики"
        ),
        typology_code="ПФТ-ОФ-01",
        typology_name_ru="Layering → офшорный VASP (DO)",
        legal_signs_ru=[
            "п. 5 ч. 2 ст. 6 115-ФЗ — офшорные юрисдикции",
            "п. 2 ч. 2 ст. 6 115-ФЗ — структурирование / размывание следа",
            "п. 1 ч. 2 ст. 6 115-ФЗ — операции с ЦФА",
        ],
        instruments=["ИЦ-01", "ИЦ-03", "ИЦ-06", "ИЦ-07", "ИЦ-08"],
        subject_category_ru="Физическое лицо — P2P-участник",
        case_series="КД-2026",
    ),
    "sbp_gray_hub": ScenarioAlertMeta(
        scenario_id="sbp_gray_hub",
        official_title_ru=(
            "Автоматическое выявление: агрегирующий hub-кошелёк "
            "(СБП → массовый fan-out, exposure mixer)"
        ),
        typology_code="ПФТ-СБП-04",
        typology_name_ru="СБП → серый OTC-агрегатор → mixer",
        legal_signs_ru=[
            "п. 2 ч. 2 ст. 6 115-ФЗ — структурирование через множество контрагентов",
            "п. 1 ч. 2 ст. 6 115-ФЗ — операции с ЦФА (USDT/TRON)",
            "п. 6 ч. 2 ст. 6 115-ФЗ — связь с anonymizing services (mixer)",
        ],
        instruments=["ИЦ-02", "ИЦ-03", "ИЦ-05", "ИЦ-07", "ИЦ-08"],
        subject_category_ru="Неидентифицированный OTC-агрегатор",
        case_series="КД-2026",
    ),
}


PATTERN_META: dict[str, dict[str, Any]] = {
    "hub_fanout_anomaly": {
        "code": "MON-PAT-001",
        "official_title_ru": (
            "MON-PAT-001: Агрегирующий кошелёк — аномальный fan-in/fan-out "
            "(признак серого СБП→крипто канала)"
        ),
        "typology_code": "ПФТ-СБП-04",
    },
    "cis_corridor_ru_kz": {
        "code": "MON-PAT-002",
        "official_title_ru": (
            "MON-PAT-002: Транзитный коридор РФ → KZ — цепочка "
            "промежуточных кошельков TRON"
        ),
        "typology_code": "ПФТ-ТР-02",
    },
    "p2p_offshore_72h": {
        "code": "MON-PAT-003",
        "official_title_ru": (
            "MON-PAT-003: P2P-рубли → офшорный CEX в течение 72 часов "
            "(корреляция STR + on-chain)"
        ),
        "typology_code": "ПФТ-ЦФА-03",
    },
    "layering_offshore_do": {
        "code": "MON-PAT-004",
        "official_title_ru": (
            "MON-PAT-004: Layering TRON с выходом на VASP "
            "в офшорной юрисдикции (DO)"
        ),
        "typology_code": "ПФТ-ОФ-01",
    },
}


_seq_bank = 0
_seq_mon = 0
_seq_case = 480


def _next_case_ref(series: str) -> str:
    global _seq_case
    _seq_case += 1
    return f"{series}-{_seq_case:05d}"


def format_bank_alert_code(feed: BankRegulatorFeed) -> str:
    global _seq_bank
    _seq_bank += 1
    bic = (feed.bank_bic or "UNKNOWN")[:8]
    dt = feed.observed_at[:10].replace("-", "") if feed.observed_at else "00000000"
    return f"STR-{bic}-{dt}-{_seq_bank:03d}"


def format_monitor_alert_code(pattern_id: str) -> str:
    global _seq_mon
    _seq_mon += 1
    pat = PATTERN_META.get(pattern_id, {}).get("code", pattern_id.upper())
    dt = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{pat}-{dt}-{_seq_mon:02d}"


def bank_alert_title(feed: BankRegulatorFeed) -> str:
    type_label = BANK_ALERT_TYPE_LABELS.get(feed.alert_type, feed.alert_type)
    return f"{type_label} · {feed.bank_name}"


def bank_alert_summary(feed: BankRegulatorFeed, meta: ScenarioAlertMeta) -> str:
    amount_str = f"{feed.amount:,.0f} {feed.currency or 'RUB'}" if feed.amount else "—"
    return (
        f"Входящее сообщение по линии хаба регулятора (115-ФЗ, ч. 1 ст. 7). "
        f"Кредитная организация: {feed.bank_name}. Сумма операции: {amount_str}. "
        f"Типология: {meta.typology_code} — {meta.typology_name_ru}. "
        f"Feed ID: {feed.feed_id}."
    )


def get_scenario_meta(scenario_id: str) -> ScenarioAlertMeta:
    return SCENARIO_META[scenario_id]
