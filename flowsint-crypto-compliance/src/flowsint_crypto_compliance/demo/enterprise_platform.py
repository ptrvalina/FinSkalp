"""
Платформа Flowsint Compliance — суверенные модули и источники (полностью на русском).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ModuleStatus = Literal["operational", "degraded", "standby"]

MODULE_STATUS_RU: dict[str, str] = {
    "operational": "Работает",
    "degraded": "Частично",
    "standby": "Ожидание",
}


@dataclass(frozen=True)
class PlatformModule:
    code: str
    ic_code: str
    name_ru: str
    suite_ru: str
    capability_tag_ru: str
    description_ru: str
    capabilities_ru: list[str]
    status: ModuleStatus = "operational"
    sla_pct: float = 99.97

    def to_dict(self) -> dict[str, Any]:
        status_ru = {
            "operational": "Работает",
            "degraded": "Частично",
            "standby": "Ожидание",
        }.get(self.status, self.status)
        return {
            "code": self.code,
            "ic_code": self.ic_code,
            "name_ru": self.name_ru,
            "suite_ru": self.suite_ru,
            "capability_tag_ru": self.capability_tag_ru,
            "description_ru": self.description_ru,
            "capabilities_ru": self.capabilities_ru,
            "status": self.status,
            "status_ru": status_ru,
            "health_label_ru": status_ru,
        }


PLATFORM_MODULES: list[PlatformModule] = [
    PlatformModule(
        "INST_HUB", "ИЦ-01", "Банковский хаб регулятора", "Приём данных",
        "Институциональный приём данных банков",
        "Приём STR/SAR от 100 банков через единый шлюз 115-ФЗ. Валидация, обогащение, маршрутизация в OSINT.",
        ["STR/SAR", "Hub v1", "100 банков", "Real-time"],
    ),
    PlatformModule(
        "TX_MON", "ИЦ-02", "Мониторинг транзакций (KYT)", "Мониторинг",
        "Непрерывный транзакционный мониторинг",
        "Непрерывный мониторинг: типологии, структурирование, VASP, санкции, cross-chain.",
        ["47 сценариев", "TRON/BTC/ETH", "Алерты", "<50 мс"],
        sla_pct=99.95,
    ),
    PlatformModule(
        "REACTOR", "ИЦ-03", "OSINT Fusion · Граф расследования", "OSINT",
        "Граф расследования и multi-hop трассировка",
        "Ядро OSINT: граф кошельков, VASP, фиат-якорей. Multi-hop, кластеры, экспорт доказательств.",
        ["Fusion engine", "Evidence graph", "Multi-hop", "Экспорт"],
    ),
    PlatformModule(
        "HOLISTIC", "ИЦ-04", "Суверенный скрининг", "Скрининг",
        "Скрининг VASP/OTC на суверенных данных",
        "Скрининг 1 000+ OTC/VASP. Чёрная/серая зона. Только суверенные источники РФ/СНГ.",
        ["1 000+ OTC", "Кластеры", "Risk bands", "Реестр"],
        sla_pct=99.94,
    ),
    PlatformModule(
        "INTEL_GATE", "ИЦ-05", "Реестр суверенных риск-меток", "Реестры",
        "Реестр 115-ФЗ и внутренние списки РФ/СНГ",
        "Импорт перечня Росфинмониторинга (115-ФЗ) и внутренних списков. При конфликте — суверенный источник.",
        ["Перечень 115-ФЗ", "Санкции РФ", "Merge engine", "Спорные метки"],
        sla_pct=99.92,
    ),
    PlatformModule(
        "CORRIDOR", "ИЦ-06", "Трансграничная аналитика", "Аналитика",
        "Коридоры РФ/СНГ/офшор и предсказание связей",
        "Коридоры РФ/СНГ/офшор, layering, VASP exit, предсказание связей в графе.",
        ["14 коридоров", "Jurisdiction risk", "Мосты", "AI"],
        sla_pct=99.93,
    ),
    PlatformModule(
        "RISK_ENGINE", "ИЦ-07", "Движок финансового риска", "Детекция",
        "Единый индекс риска и приоритизация",
        "Единый индекс 0–100, typology weights, governance моделей, illicit flow.",
        ["Скоринг", "Typology", "Governance", "Приоритизация"],
    ),
    PlatformModule(
        "CASE_SAR", "ИЦ-08", "Дела и отчётность 115-ФЗ", "Кейсы",
        "Workflow дел и справки 115-ФЗ",
        "Workflow: triage → расследование → справка 115-ФЗ → audit trail.",
        ["Кейсы", "115-ФЗ", "Audit", "KYC контекст"],
        sla_pct=99.98,
    ),
    PlatformModule(
        "KYC_BRIDGE", "—", "Мост идентификации KYC/KYB", "Идентификация",
        "Резолюция субъекта на данных банковского KYC",
        "Резолюция субъекта, документы, обогащение из банковского KYC (ЕСИА/КЭДО).",
        ["KYC", "KYB", "PEP touchpoint"],
        sla_pct=99.91,
    ),
    PlatformModule(
        "SCENARIO", "—", "Студия сценариев", "Детекция",
        "Редактор типологий и backtesting",
        "Настройка сценариев, FP review, champion/challenger, backtesting.",
        ["Редактор", "Backtest", "Champion/challenger"],
        sla_pct=99.90,
    ),
]

MODULE_BY_IC = {m.ic_code: m for m in PLATFORM_MODULES if m.ic_code != "—"}
MODULE_BY_CODE = {m.code: m for m in PLATFORM_MODULES}

# Суверенные источники данных РФ/СНГ (без зависимости от иностранных сервисов)
SOVEREIGN_SOURCES = [
    {"id": "bank_hub", "name": "Банковский хаб (115-ФЗ)", "products_ru": ["STR/SAR", "100 банков"], "status": "connected", "mode_ru": "Единый шлюз регулятора, real-time"},
    {"id": "onchain", "name": "Публичный блокчейн", "products_ru": ["BTC", "ETH", "TRON"], "status": "connected", "mode_ru": "Собственные ноды, без закрытых API бирж"},
    {"id": "control_purchase", "name": "Контрольные закупки", "products_ru": ["P2P", "OTC"], "status": "connected", "mode_ru": "Оперативное заземление каналов"},
    {"id": "vasp_licensed", "name": "Лицензированные VASP (РФ/СНГ)", "products_ru": ["Депозиты", "Выводы"], "status": "connected", "mode_ru": "Площадки с лицензией ЦБ/локального регулятора"},
    {"id": "rosfinmonitoring", "name": "Перечень Росфинмониторинга", "products_ru": ["115-ФЗ", "Санкции РФ"], "status": "connected", "mode_ru": "Официальный перечень, ежедневная сверка"},
    {"id": "otc_registry", "name": "Реестр серых OTC", "products_ru": ["1 000+ обменников"], "status": "connected", "mode_ru": "Собственная OSINT-разведка"},
    {"id": "cis_partner", "name": "Обмен с ФИУ СНГ", "products_ru": ["Двусторонний обмен"], "status": "connected", "mode_ru": "АФМ РК, БелФМ и др."},
    {"id": "open_osint", "name": "Открытый OSINT", "products_ru": ["Telegram", "Форумы"], "status": "connected", "mode_ru": "Публичные каналы и утечки"},
]


def list_platform_modules() -> list[dict[str, Any]]:
    return [m.to_dict() for m in PLATFORM_MODULES]


def get_platform_overview() -> dict[str, Any]:
    return {
        "platform_name_ru": "Flowsint Compliance",
        "platform_tagline_ru": "OSINT · Мониторинг операций · ПОД/ФТ · Суверенный контур РФ/СНГ",
        "modules_total": len(PLATFORM_MODULES),
        "microservices_total": 24,
        "modules_operational": sum(1 for m in PLATFORM_MODULES if m.status == "operational"),
        "integrations": SOVEREIGN_SOURCES,
        "certifications_ru": ["115-ФЗ", "281-ФЗ", "259-ФЗ", "ФАТФ Rec.15/16", "ISO 27001"],
    }
