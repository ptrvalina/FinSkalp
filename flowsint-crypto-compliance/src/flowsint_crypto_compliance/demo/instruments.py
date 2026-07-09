"""
Реестр инструментов боевого контура ПОД/ФТ (РФ).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

InstrumentCategory = Literal["ingestion", "analysis", "detection", "reporting"]


@dataclass(frozen=True)
class ComplianceInstrument:
    code: str
    name_ru: str
    category: InstrumentCategory
    category_label_ru: str
    description_ru: str
    legal_refs: list[str]
    status: Literal["active", "standby"] = "active"
    version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "name_ru": self.name_ru,
            "category": self.category,
            "category_label_ru": self.category_label_ru,
            "description_ru": self.description_ru,
            "legal_refs": self.legal_refs,
            "status": self.status,
            "version": self.version,
        }


CATEGORY_LABELS: dict[InstrumentCategory, str] = {
    "ingestion": "Приём и интеграция",
    "analysis": "Аналитика и OSINT",
    "detection": "Выявление рисков",
    "reporting": "Отчётность и решения",
}


INSTRUMENTS: list[ComplianceInstrument] = [
    ComplianceInstrument(
        code="ИЦ-01",
        name_ru="Хаб банковских сообщений",
        category="ingestion",
        category_label_ru=CATEGORY_LABELS["ingestion"],
        description_ru=(
            "Приём STR/SAR, информации по 115-ФЗ и 281-ФЗ от уполномоченных банков "
            "через единый шлюз регулятора. Валидация JSON Schema hub v1."
        ),
        legal_refs=["115-ФЗ ст. 7", "281-ФЗ ст. 8", "Указание Банка России № 4937-У"],
    ),
    ComplianceInstrument(
        code="ИЦ-02",
        name_ru="Монитор транзакционных паттернов",
        category="ingestion",
        category_label_ru=CATEGORY_LABELS["ingestion"],
        description_ru=(
            "Непрерывный on-chain мониторинг: hub/fan-out, структурирование, "
            "аномальные коридоры СБП→крипто, транзит СНГ."
        ),
        legal_refs=["115-ФЗ ст. 6", "Методические рекомендации Росфинмониторинга"],
    ),
    ComplianceInstrument(
        code="ИЦ-03",
        name_ru="OSINT Fusion Engine",
        category="analysis",
        category_label_ru=CATEGORY_LABELS["analysis"],
        description_ru=(
            "Сведение банковских, лицензированных площадок, контрольных закупок "
            "и KYT в единый граф доказательств с приоритетом суверенных источников."
        ),
        legal_refs=["115-ФЗ ст. 7 ч. 5", "259-ФЗ (ЦФА)"],
    ),
    ComplianceInstrument(
        code="ИЦ-04",
        name_ru="Суверенная крипто-атрибуция (РФ/СНГ)",
        category="analysis",
        category_label_ru=CATEGORY_LABELS["analysis"],
        description_ru=(
            "Кластеризация, профилирование регионов, чёрная/серая зона на "
            "суверенных источниках РФ/СНГ."
        ),
        legal_refs=["Стратегия ПОД/ФТ РФ", "Нац. интересы в сфере ЦФА"],
    ),
    ComplianceInstrument(
        code="ИЦ-05",
        name_ru="Реестр суверенных риск-меток",
        category="analysis",
        category_label_ru=CATEGORY_LABELS["analysis"],
        description_ru=(
            "Импорт перечня Росфинмониторинга (115-ФЗ) и внутренних списков РФ/СНГ. "
            "При конфликте приоритет имеет суверенный источник."
        ),
        legal_refs=["115-ФЗ ст. 6, ст. 7", "Перечень Росфинмониторинга"],
    ),
    ComplianceInstrument(
        code="ИЦ-06",
        name_ru="Анализатор трансграничных коридоров",
        category="analysis",
        category_label_ru=CATEGORY_LABELS["analysis"],
        description_ru=(
            "Выявление цепочек RU→СНГ→офшор, layering, выход на VASP "
            "в юрисдикциях повышенного риска."
        ),
        legal_refs=["115-ФЗ ст. 6 п. 2", "ФАТФ Rec. 15/16 (VASP)"],
    ),
    ComplianceInstrument(
        code="ИЦ-07",
        name_ru="Детектор нелегальных потоков ценностей",
        category="detection",
        category_label_ru=CATEGORY_LABELS["detection"],
        description_ru=(
            "Скоринг признаков обхода, mixer/exchange exposure, "
            "склейка фиат↔крипто, подтверждение STR контрольными закупками."
        ),
        legal_refs=["115-ФЗ ст. 6", "Перечень признаков подозрительных операций"],
    ),
    ComplianceInstrument(
        code="ИЦ-08",
        name_ru="Формирование отчётности ПОД/ФТ",
        category="reporting",
        category_label_ru=CATEGORY_LABELS["reporting"],
        description_ru=(
            "Справки по результатам проверки, решения о направлении сообщений "
            "в Росфинмониторинг, реестр материалов проверки."
        ),
        legal_refs=["115-ФЗ ст. 7–8", "115-ФЗ ст. 6 ч. 1–2", "281-ФЗ"],
    ),
]

INSTRUMENT_BY_CODE = {i.code: i for i in INSTRUMENTS}


def list_instruments() -> list[dict[str, Any]]:
    return [i.to_dict() for i in INSTRUMENTS]


def instruments_for_investigation() -> list[str]:
    return [i.code for i in INSTRUMENTS if i.status == "active"]
