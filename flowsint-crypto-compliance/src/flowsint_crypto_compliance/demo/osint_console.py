"""
Центр OSINT — источники, fusion, граф доказательств (демо API).
"""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.demo.demo_context import get_demo_label_cache
from flowsint_crypto_compliance.demo.osint_runtime import run_phased_fusion

OSINT_SOURCES: list[dict[str, Any]] = [
    {
        "id": "bank_115fz",
        "name_ru": "Банковский хаб (115-ФЗ)",
        "type": "domestic",
        "priority": 1,
        "description_ru": "STR/SAR от 100 уполномоченных банков через единый шлюз регулятора.",
        "records_24h": 2847,
        "trust_weight": 1.0,
    },
    {
        "id": "onchain_public",
        "name_ru": "Публичный блокчейн (BTC/ETH/TRON)",
        "type": "technical",
        "priority": 2,
        "description_ru": "TronGrid + mempool.space — live TRC20/BTC transfers, multi-hop fusion.",
        "records_24h": 2_100_000,
        "trust_weight": 0.95,
    },
    {
        "id": "control_purchase",
        "name_ru": "Контрольные закупки (P2P/OTC)",
        "type": "operational",
        "priority": 2,
        "description_ru": "Оперативное заземление каналов — прямое доказательство для суда и регулятора.",
        "records_24h": 34,
        "trust_weight": 0.98,
    },
    {
        "id": "vasp_licensed",
        "name_ru": "Лицензированные VASP (РФ/СНГ)",
        "type": "domestic",
        "priority": 2,
        "description_ru": "Депозиты/выводы на площадках с лицензией ЦБ/локального регулятора.",
        "records_24h": 892,
        "trust_weight": 0.92,
    },
    {
        "id": "otc_registry",
        "name_ru": "Реестр серых OTC (1 000+)",
        "type": "sovereign",
        "priority": 3,
        "description_ru": "Собственная разведка: Telegram OTC, P2P, СБП→крипто, hawala.",
        "records_24h": 12400,
        "trust_weight": 0.88,
    },
    {
        "id": "rosfinmonitoring",
        "name_ru": "Перечень Росфинмониторинга (115-ФЗ)",
        "type": "sovereign",
        "priority": 1,
        "description_ru": "Официальный перечень и санкционные списки РФ. Ежедневная сверка.",
        "records_24h": 18420,
        "trust_weight": 0.99,
    },
    {
        "id": "cis_partner",
        "name_ru": "Обмен с ФИУ СНГ (АФМ РК, БелФМ)",
        "type": "sovereign",
        "priority": 2,
        "description_ru": "Двусторонний обмен риск-метками с финразведками СНГ.",
        "records_24h": 96500,
        "trust_weight": 0.9,
    },
    {
        "id": "internal_osint",
        "name_ru": "Внутренняя OSINT-разведка (реестр меток)",
        "type": "sovereign",
        "priority": 3,
        "description_ru": "Собственный реестр риск-меток по адресам и кластерам РФ/СНГ.",
        "records_24h": 1204000,
        "trust_weight": 0.85,
    },
    {
        "id": "open_osint",
        "name_ru": "FinSkalp Scalpel · 8 легальных коллекторов",
        "type": "open",
        "priority": 5,
        "description_ru": (
            "On-chain, санкции, Maigret, abuse-реестры, Ahmia, VASP, enforcement, RDAP. "
            "Без слитых БД и украденных ПДн."
        ),
        "records_24h": 156000,
        "trust_weight": 0.62,
    },
    {
        "id": "maigret",
        "name_ru": "Maigret · username 3000+",
        "type": "open",
        "priority": 5,
        "description_ru": "Профили по нику на тысячах площадок (Sherlock/Maigret).",
        "records_24h": 42000,
        "trust_weight": 0.58,
    },
    {
        "id": "spiderfoot",
        "name_ru": "SpiderFoot · 200+ модулей",
        "type": "open",
        "priority": 5,
        "description_ru": "DNS, WHOIS, web spider, публичные индексы.",
        "records_24h": 88000,
        "trust_weight": 0.6,
    },
    {
        "id": "open_sanctions",
        "name_ru": "OpenSanctions",
        "type": "open",
        "priority": 4,
        "description_ru": "Глобальные санкционные и PEP-списки (открытые данные).",
        "records_24h": 210000,
        "trust_weight": 0.75,
    },
    {
        "id": "mempool_trongrid",
        "name_ru": "mempool.space · TronGrid",
        "type": "technical",
        "priority": 3,
        "description_ru": "Публичные API BTC/TRON без иностранного KYT.",
        "records_24h": 3_400_000,
        "trust_weight": 0.9,
    },
    {
        "id": "dns_intel",
        "name_ru": "DNS / домены из OSINT",
        "type": "technical",
        "priority": 6,
        "description_ru": "Связка доменов из упоминаний с публичным DNS.",
        "records_24h": 12400,
        "trust_weight": 0.52,
    },
]

FUSION_PIPELINE_RU: list[dict[str, str]] = [
    {"step": "ingest", "label_ru": "1. Приём и нормализация источников"},
    {"step": "entity", "label_ru": "2. Резолвер сущностей (кошелёк = кластер)"},
    {"step": "merge", "label_ru": "3. Слияние: суверенные > банк > VASP > реестр"},
    {"step": "graph", "label_ru": "4. Построение графа доказательств"},
    {"step": "link", "label_ru": "5. Склейка фиат ↔ крипто (linkage score)"},
    {"step": "attribute", "label_ru": "6. Суверенная атрибуция (РФ/СНГ)"},
    {"step": "bridge", "label_ru": "7. Трансграничные мосты и коридоры"},
    {"step": "detect", "label_ru": "8. Детектор + XGBoost risk"},
]


class OSINTConsole:
    def status(self) -> dict[str, Any]:
        cache = get_demo_label_cache()
        return {
            "fusion_engine": "operational",
            "sources_active": len(OSINT_SOURCES),
            "sovereign_mode": True,
            "registry_mode": "sovereign",
            "registry_labels_loaded": cache.count(),
            "live_chain_apis": True,
            "live_collectors": [
                "trongrid",
                "mempool.space",
                "opensanctions",
                "bitcoinabuse",
                "maigret",
                "ahmia",
            ],
            "multihop_fusion": "enabled",
            "postgres_required": False,
        }

    def sources(self) -> list[dict[str, Any]]:
        return OSINT_SOURCES

    def pipeline(self) -> list[dict[str, str]]:
        return FUSION_PIPELINE_RU

    async def run_fusion(self, scenario_id: str = "p2p_rub_offshore") -> dict[str, Any]:
        steps_out: list[dict[str, Any]] = []

        async def on_phase(step_id: str, label_ru: str, detail: dict[str, Any]) -> None:
            steps_out.append(
                {
                    "id": step_id,
                    "label_ru": label_ru,
                    "status": "done",
                    "detail_ru": _format_step_detail(detail),
                }
            )

        phased = await run_phased_fusion(scenario_id, on_phase=on_phase)
        d = phased.report
        graph = phased.fusion.graph
        return {
            "summary_ru": (
                f"OSINT Fusion завершён за {phased.duration_ms} мс. "
                f"Граф: {len(graph.nodes)} узлов, {len(graph.edges)} рёбер. "
                f"Индекс риска: {d['illegal_flow_score']:.0f}/100."
            ),
            "steps": steps_out,
            "sources_used": [s["id"] for s in OSINT_SOURCES[:6]],
            "report": d,
            "corridor_matches": phased.fusion.corridor_matches,
            "evidence_highlights_ru": _evidence_highlights(d),
        }


def _format_step_detail(detail: dict[str, Any]) -> str:
    from flowsint_crypto_compliance.demo.osint_runtime import _format_detail

    return _format_detail(detail)


def _evidence_highlights(report: dict) -> list[str]:
    items = []
    for f in report.get("findings", [])[:5]:
        items.append(f"[{f['severity'].upper()}] {f['title_ru']}")
    m = report.get("metrics", {})
    if m.get("bank_crypto_links"):
        items.append(f"Склейка банк↔крипто: {m['bank_crypto_links']} подтверждённых связей")
    if m.get("gray_zone_reduction_pct"):
        items.append(f"Серая зона сужена на {m['gray_zone_reduction_pct']}%")
    return items
