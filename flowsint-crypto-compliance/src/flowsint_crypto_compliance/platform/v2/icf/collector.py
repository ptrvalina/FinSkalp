"""RFC-0014 Ch.3, 19 — ICF collector wrapping Connector."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.connectors.base import Connector
from flowsint_crypto_compliance.platform.v2.icf.normalizer import ConnectorNormalizer, get_normalizer
from flowsint_crypto_compliance.platform.v2.icf.types import CollectorLifecycle
from flowsint_crypto_compliance.platform.v2.icf.validator import ConnectorValidator, get_validator

# Architectural constraint Ch.19 — forbidden direct imports
_FORBIDDEN_MODULES = frozenset(
    {
        "flowsint_crypto_compliance.platform.v2.knowledge_graph",
        "flowsint_crypto_compliance.platform.v2.knowledge_store",
        "flowsint_crypto_compliance.platform.v2.entity_resolution",
    }
)


class ICFCollector:
    """
    Wraps RFC-0007 Connector with ICF lifecycle.
    MUST NOT mutate graph / risk / entity resolution — publish is orchestrator-only.
    """

    def __init__(
        self,
        connector: Connector,
        *,
        normalizer: ConnectorNormalizer | None = None,
        validator: ConnectorValidator | None = None,
    ) -> None:
        self.connector = connector
        self._normalizer = normalizer or get_normalizer()
        self._validator = validator or get_validator()
        self._stages: list[str] = []

    @property
    def connector_id(self) -> str:
        return self.connector.descriptor.connector_id

    @property
    def stages_completed(self) -> list[str]:
        return list(self._stages)

    async def initialize(self) -> dict[str, Any]:
        result = await self.connector.connect()
        self._stages.append(CollectorLifecycle.INITIALIZE.value)
        return result

    async def authenticate(self) -> dict[str, Any]:
        result = await self.connector.authenticate()
        self._stages.append(CollectorLifecycle.AUTHENTICATE.value)
        return result

    async def collect(self, *, query: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        records = await self.connector.collect(query=query)
        self._stages.append(CollectorLifecycle.COLLECT.value)
        return records

    def normalize(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = self._normalizer.normalize(self.connector, records)
        self._stages.append(CollectorLifecycle.NORMALIZE.value)
        return normalized

    def validate(self, records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
        valid, errors = self._validator.validate(self.connector, records)
        self._stages.append(CollectorLifecycle.VALIDATE.value)
        return valid, errors

    async def publish(self, *_args: Any, **_kwargs: Any) -> int:
        """ICF Ch.19 — collector does not publish to KG; orchestrator handles downstream."""
        self._stages.append(CollectorLifecycle.PUBLISH.value)
        return 0

    async def shutdown(self) -> None:
        await self.connector.shutdown()
        self._stages.append(CollectorLifecycle.SHUTDOWN.value)

    @staticmethod
    def architectural_constraints() -> dict[str, Any]:
        return {
            "forbidden": [
                "direct_knowledge_graph_mutation",
                "direct_risk_scoring",
                "entity_resolution_bypass",
                "analytical_decisions",
            ],
            "forbidden_modules": sorted(_FORBIDDEN_MODULES),
            "publish_delegated_to": "orchestrator.fusion_bridge + kg_bridge",
        }
