"""Базовый контракт коллекторов FinSkalp Scalpel (паттерн SpiderFoot modules)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from flowsint_crypto_compliance.osint_core.open_source_collector import OpenMentionHit
from flowsint_crypto_compliance.osint_core.scalpel.network_gateway import NetworkGateway
from flowsint_types.fiat_crypto import Chain


@dataclass
class CollectorResult:
    collector_id: str
    hits: list[OpenMentionHit] = field(default_factory=list)
    status: str = "ok"
    detail: str = ""
    entities: dict[str, Any] = field(default_factory=dict)

    def to_status(self) -> str:
        if self.status != "ok":
            return f"{self.status}:{self.detail}" if self.detail else self.status
        return f"hits:{len(self.hits)}" if self.hits else "miss"


class ScalpelCollector(ABC):
    collector_id: str = "base"
    name_ru: str = ""
    routes: tuple[str, ...] = ("clearnet",)
    inspired_by: str = ""

    def __init__(self, gateway: NetworkGateway) -> None:
        self._gw = gateway

    @abstractmethod
    async def collect(
        self,
        address: str,
        chain: Chain,
        *,
        counterparties: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> CollectorResult:
        ...
