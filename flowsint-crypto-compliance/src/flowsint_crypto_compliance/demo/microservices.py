"""
Микросервисная архитектура платформы Flowsint Compliance (демо-стенд).
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any, Literal

ServiceStatus = Literal["healthy", "degraded", "starting"]
ServiceLayer = Literal["gateway", "ingestion", "osint", "analytics", "detection", "storage", "reporting"]


@dataclass(frozen=True)
class Microservice:
    id: str
    name_ru: str
    layer: ServiceLayer
    layer_label_ru: str
    description_ru: str
    tech: str
    replicas: int
    depends_on: tuple[str, ...]
    ic_code: str | None = None

    def to_dict(self, *, latency_ms: int | None = None, status: ServiceStatus = "healthy") -> dict[str, Any]:
        return {
            "id": self.id,
            "name_ru": self.name_ru,
            "layer": self.layer,
            "layer_label_ru": self.layer_label_ru,
            "description_ru": self.description_ru,
            "tech": self.tech,
            "replicas": self.replicas,
            "depends_on": list(self.depends_on),
            "ic_code": self.ic_code,
            "status": status,
            "latency_ms": latency_ms if latency_ms is not None else _latency(self.id),
            "uptime_pct": round(99.9 + random.Random(hash(self.id) % 997).random() * 0.09, 2),
        }


LAYER_LABELS: dict[ServiceLayer, str] = {
    "gateway": "Шлюз и API",
    "ingestion": "Приём данных",
    "osint": "OSINT · разведка",
    "analytics": "Аналитика",
    "detection": "Детекция",
    "storage": "Хранилища",
    "reporting": "Отчётность",
}

MICROSERVICES: list[Microservice] = [
    Microservice("ms-api-gateway", "API Gateway регулятора", "gateway", LAYER_LABELS["gateway"],
                 "Единая точка входа, rate-limit, JWT, маршрутизация к сервисам.", "FastAPI + Nginx", 3, ()),
    Microservice("ms-hub-bank", "Хаб банковских сообщений", "ingestion", LAYER_LABELS["ingestion"],
                 "STR/SAR от 100 банков, валидация hub v1, 115-ФЗ.", "Python + Kafka", 4, ("ms-api-gateway",), "ИЦ-01"),
    Microservice("ms-tx-monitor", "Мониторинг транзакций (KYT)", "ingestion", LAYER_LABELS["ingestion"],
                 "Real-time паттерны, typology engine, TRON/BTC/ETH.", "Python + Redis", 5, ("ms-api-gateway",), "ИЦ-02"),
    Microservice("ms-registry-import", "Импорт суверенного реестра меток", "ingestion", LAYER_LABELS["ingestion"],
                 "Перечень Росфинмониторинга (115-ФЗ) и внутренние списки РФ/СНГ.", "Python + S3", 2, ("ms-api-gateway",), "ИЦ-05"),
    Microservice("ms-osint-fusion", "OSINT Fusion Engine", "osint", LAYER_LABELS["osint"],
                 "Ядро: сведение всех источников в единый граф доказательств.", "Python async", 6, ("ms-hub-bank", "ms-registry-import"), "ИЦ-03"),
    Microservice("ms-osint-graph", "Граф доказательств", "osint", LAYER_LABELS["osint"],
                 "Evidence graph: узлы, рёбра, provenance, экспорт.", "Python + in-memory", 4, ("ms-osint-fusion",)),
    Microservice("ms-osint-entity", "Резолвер сущностей", "osint", LAYER_LABELS["osint"],
                 "Дедупликация кошельков, кластеров, субъектов.", "Python", 3, ("ms-osint-fusion",)),
    Microservice("ms-osint-link", "Скоринг связей фиат↔крипто", "osint", LAYER_LABELS["osint"],
                 "Linkage score, склейка банк→адрес→VASP.", "Python", 3, ("ms-osint-graph", "ms-osint-entity")),
    Microservice("ms-osint-merge", "Движок слияния источников", "osint", LAYER_LABELS["osint"],
                 "Приоритет: суверенные > банк > VASP > реестр. Спорные метки.", "Python", 2, ("ms-osint-fusion", "ms-registry-import")),
    Microservice("ms-sovereign", "Суверенная атрибуция РФ/СНГ", "osint", LAYER_LABELS["osint"],
                 "Чёрная/серая зона, коридоры, суверенная модель РФ/СНГ.", "Python", 4, ("ms-osint-merge",), "ИЦ-04"),
    Microservice("ms-chain-tron", "Адаптер TRON", "osint", LAYER_LABELS["osint"],
                 "On-chain TRON, TronGrid, USDT TRC-20.", "Python + httpx", 3, ("ms-osint-fusion",)),
    Microservice("ms-chain-btc", "Адаптер Bitcoin", "osint", LAYER_LABELS["osint"],
                 "UTXO, Blockstream API, peel chain.", "Python + httpx", 2, ("ms-osint-fusion",)),
    Microservice("ms-chain-eth", "Адаптер Ethereum", "osint", LAYER_LABELS["osint"],
                 "EVM, Etherscan, токены ERC-20.", "Python + httpx", 2, ("ms-osint-fusion",)),
    Microservice("ms-control-purchase", "Контрольные закупки", "osint", LAYER_LABELS["osint"],
                 "Оперативное заземление P2P/OTC каналов.", "Python", 2, ("ms-osint-fusion",)),
    Microservice("ms-corridor", "Анализатор коридоров", "analytics", LAYER_LABELS["analytics"],
                 "RU→СНГ→офшор, трансграничные мосты.", "Python", 3, ("ms-sovereign",), "ИЦ-06"),
    Microservice("ms-risk-engine", "Движок риск-скоринга", "detection", LAYER_LABELS["detection"],
                 "Индекс 0–100, typology weights, illicit flow.", "Python", 4, ("ms-osint-link", "ms-corridor"), "ИЦ-07"),
    Microservice("ms-pattern-engine", "Движок сценариев и типологий", "detection", LAYER_LABELS["detection"],
                 "47 активных сценариев, champion/challenger.", "Python", 2, ("ms-tx-monitor",)),
    Microservice("ms-registry-vasp", "Реестр VASP/OTC", "storage", LAYER_LABELS["storage"],
                 "1 000+ серых обменников, intelligence graph.", "PostgreSQL", 2, ()),
    Microservice("ms-registry-banks", "Реестр банков", "storage", LAYER_LABELS["storage"],
                 "100 уполномоченных банков, BIC, tier.", "PostgreSQL", 2, ()),
    Microservice("ms-case-manager", "Менеджер расследований", "reporting", LAYER_LABELS["reporting"],
                 "Очередь дел, triage, workflow, audit trail.", "Python + PostgreSQL", 3, ("ms-risk-engine",), "ИЦ-08"),
    Microservice("ms-fz115", "Формирование отчётов 115-ФЗ", "reporting", LAYER_LABELS["reporting"],
                 "Справки, решения, реестр материалов проверки.", "Python", 2, ("ms-case-manager",), "ИЦ-08"),
    Microservice("ms-sanctions", "Санкции и перечень 115-ФЗ", "ingestion", LAYER_LABELS["ingestion"],
                 "Сверка с перечнем Росфинмониторинга и санкционными списками РФ.", "Python", 2, ("ms-registry-import",)),
    Microservice("ms-vault", "Vault секретов", "gateway", LAYER_LABELS["gateway"],
                 "API keys, bank credentials, ключи нод и реестров.", "HashiCorp Vault", 2, ()),
    Microservice("ms-audit-trail", "Журнал аудита и трассировка", "reporting", LAYER_LABELS["reporting"],
                 "Immutable audit log: каждое действие аналитика, экспорт для проверки.", "PostgreSQL + Kafka", 2, ("ms-api-gateway",)),
]

SERVICE_BY_ID = {s.id: s for s in MICROSERVICES}


def _latency(sid: str) -> int:
    base = {"ms-osint-fusion": 28, "ms-osint-graph": 15, "ms-api-gateway": 4}.get(sid, 12)
    return base + random.randint(0, 8)


def list_microservices() -> list[dict[str, Any]]:
    return [s.to_dict() for s in MICROSERVICES]


def get_mesh_topology() -> dict[str, Any]:
    layers: dict[str, list[dict]] = {}
    for s in MICROSERVICES:
        layers.setdefault(s.layer_label_ru, []).append(s.to_dict())
    osint_count = sum(1 for s in MICROSERVICES if s.layer == "osint")
    return {
        "total_services": len(MICROSERVICES),
        "healthy": len(MICROSERVICES) - 1,
        "osint_cluster_size": osint_count,
        "layers": layers,
        "edges": _mesh_edges(),
    }


def _mesh_edges() -> list[dict[str, str]]:
    edges = []
    for s in MICROSERVICES:
        for dep in s.depends_on:
            edges.append({"from": dep, "to": s.id, "type": "sync"})
    return edges


async def run_microservice(service_id: str, *, scenario_id: str = "p2p_rub_offshore") -> dict[str, Any]:
    from flowsint_crypto_compliance.demo.osint_runtime import execute_microservice

    svc = SERVICE_BY_ID.get(service_id)
    if not svc:
        raise KeyError(f"Unknown service: {service_id}")
    return await execute_microservice(service_id, scenario_id=scenario_id)
