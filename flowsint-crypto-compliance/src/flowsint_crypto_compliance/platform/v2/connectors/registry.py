"""RFC-0007 Connector registry and catalog."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.connectors.base import BaseConnector, Connector
from flowsint_crypto_compliance.platform.v2.connectors.types import (
    ConnectorCategory,
    ConnectorDescriptor,
    ConnectorStatus,
    SourceQualityProfile,
)


class _StaticConnector(BaseConnector):
    async def collect(self, *, query: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        q = query or {}
        if q.get("address"):
            return [
                {
                    "entity_type": "blockchain_address",
                    "entity_value": str(q["address"]),
                    "confidence": self.descriptor.quality.trust_level,
                    "chain": q.get("chain"),
                }
            ]
        if q.get("entity_value"):
            return [
                {
                    "entity_type": str(q.get("entity_type") or "unknown"),
                    "entity_value": str(q["entity_value"]),
                    "confidence": self.descriptor.quality.trust_level,
                }
            ]
        return []


class ConnectorRegistry:
    def __init__(self) -> None:
        self._descriptors: dict[str, ConnectorDescriptor] = {}
        self._factories: dict[str, type[Connector]] = {}

    def register(
        self,
        descriptor: ConnectorDescriptor,
        factory: type[Connector] | None = None,
    ) -> None:
        self._descriptors[descriptor.connector_id] = descriptor
        self._factories[descriptor.connector_id] = factory or _StaticConnector

    def get_descriptor(self, connector_id: str) -> ConnectorDescriptor | None:
        return self._descriptors.get(connector_id)

    def create(self, connector_id: str) -> Connector:
        desc = self._descriptors.get(connector_id)
        if not desc:
            raise ValueError(f"Unknown connector: {connector_id}")
        factory = self._factories.get(connector_id) or _StaticConnector
        return factory(desc)

    def list_descriptors(self, category: ConnectorCategory | None = None) -> list[ConnectorDescriptor]:
        rows = list(self._descriptors.values())
        if category:
            rows = [r for r in rows if r.category == category]
        return rows

    def manifest(self) -> dict[str, Any]:
        by_cat: dict[str, list[dict[str, Any]]] = {}
        for d in self._descriptors.values():
            by_cat.setdefault(d.category.value, []).append(d.to_dict())
        return {
            "rfc": "RFC-0007",
            "schema_version": "7.0.0",
            "principle_ru": "Connector First — любой источник через единый интерфейс",
            "contract_methods": [
                "connect", "authenticate", "health", "collect",
                "normalize", "validate", "publish", "shutdown",
            ],
            "data_lifecycle": [
                "source", "connector", "normalizer", "validator",
                "fusion", "knowledge_graph", "analytics",
            ],
            "categories": list(by_cat.keys()),
            "connectors": [d.to_dict() for d in self._descriptors.values()],
            "connectors_by_category": by_cat,
            "total": len(self._descriptors),
        }


_registry: ConnectorRegistry | None = None


def get_connector_registry() -> ConnectorRegistry:
    global _registry
    if _registry is None:
        _registry = ConnectorRegistry()
        _bootstrap_connectors(_registry)
    return _registry


def _q(
    *,
    connector_id: str,
    category: ConnectorCategory,
    title_ru: str,
    status: ConnectorStatus = ConnectorStatus.PRODUCTION,
    official: bool = False,
    trust: float = 0.7,
    apis: list[str] | None = None,
    license_name: str = "internal",
) -> ConnectorDescriptor:
    return ConnectorDescriptor(
        connector_id=connector_id,
        category=category,
        title_ru=title_ru,
        status=status,
        license=license_name,
        apis=apis or [],
        quality=SourceQualityProfile(
            provenance=connector_id,
            official=official,
            trust_level=trust,
            completeness=0.8 if status == ConnectorStatus.PRODUCTION else 0.3,
        ),
    )


def _bootstrap_connectors(reg: ConnectorRegistry) -> None:
    # Blockchain Ch.2
    for cid, title in (
        ("chain.btc", "Bitcoin"),
        ("chain.eth", "Ethereum"),
        ("chain.tron", "Tron"),
        ("chain.bsc", "BNB Chain"),
        ("chain.polygon", "Polygon"),
        ("chain.sol", "Solana"),
        ("chain.ltc", "Litecoin"),
    ):
        reg.register(_q(connector_id=cid, category=ConnectorCategory.BLOCKCHAIN, title_ru=title, official=True, trust=0.9))

    reg.register(
        _q(
            connector_id="chain.xmr",
            category=ConnectorCategory.BLOCKCHAIN,
            title_ru="Monero (законные метаданные)",
            status=ConnectorStatus.PLANNED,
            trust=0.4,
        )
    )

    # Public explorers
    for cid, title, api in (
        ("explorer.tronscan", "TronScan", "https://tronscan.org"),
        ("explorer.etherscan", "Etherscan", "https://api.etherscan.io"),
        ("explorer.blockchair", "Blockchair", "https://api.blockchair.com"),
        ("explorer.mempool", "mempool.space", "https://mempool.space/api"),
        ("explorer.btccom", "BTC.com", "https://chain.api.btc.com"),
        ("explorer.blockchaincom", "Blockchain.com Explorer", "https://blockchain.info"),
    ):
        reg.register(
            _q(
                connector_id=cid,
                category=ConnectorCategory.PUBLIC_EXPLORER,
                title_ru=title,
                official=True,
                trust=0.85,
                apis=[api],
            )
        )

    # Blockchain intelligence providers (licensed)
    for cid, title in (
        ("bip.elliptic", "Elliptic"),
        ("bip.chainalysis", "Chainalysis"),
        ("bip.trm", "TRM Labs"),
        ("bip.crystal", "Crystal Intelligence"),
        ("bip.scorechain", "Scorechain"),
        ("bip.bitok", "BitOK"),
        ("bip.ciphertrace", "CipherTrace"),
    ):
        reg.register(
            _q(
                connector_id=cid,
                category=ConnectorCategory.BLOCKCHAIN_INTELLIGENCE,
                title_ru=title,
                status=ConnectorStatus.LICENSED,
                trust=0.88,
                license_name="commercial",
            )
        )

    # Registry
    for cid, title in (
        ("registry.ofac", "OFAC / санкции"),
        ("registry.sovereign", "Суверенный реестр FinSkalp"),
        ("registry.cis_vasp", "CIS VASP registry"),
        ("registry.corporate", "Корпоративные справочники"),
    ):
        reg.register(
            _q(
                connector_id=cid,
                category=ConnectorCategory.REGISTRY,
                title_ru=title,
                official=True,
                trust=0.92,
            )
        )

    # OSINT (scalpel collectors)
    for cid, title in (
        ("osint.onchain", "On-chain explorer collector"),
        ("osint.sanctions", "Санкционные списки"),
        ("osint.username", "Username / social"),
        ("osint.darknet", "Darknet index"),
        ("osint.news", "Новостные ресурсы"),
        ("osint.forum", "Открытые форумы"),
        ("osint.telegram", "Публичные каналы"),
        ("osint.search", "Поисковые системы"),
        ("osint.archive", "Архивы"),
        ("osint.document", "Общедоступные документы"),
    ):
        reg.register(_q(connector_id=cid, category=ConnectorCategory.OSINT, title_ru=title, trust=0.65))

    # Document
    for cid, title in (
        ("doc.pdf", "PDF"),
        ("doc.docx", "DOCX"),
        ("doc.xlsx", "XLSX"),
        ("doc.image", "Изображения"),
        ("doc.ocr", "OCR"),
        ("doc.archive", "Архивы"),
    ):
        reg.register(_q(connector_id=cid, category=ConnectorCategory.DOCUMENT, title_ru=title, trust=0.75))
