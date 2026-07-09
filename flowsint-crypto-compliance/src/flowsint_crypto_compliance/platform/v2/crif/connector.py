"""RFC-0015 Ch.4 — RegistryConnector wrapping RFC-0007 registry connectors."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.connectors.base import Connector
from flowsint_crypto_compliance.platform.v2.crif.normalizer import RegistryNormalizer, get_registry_normalizer
from flowsint_crypto_compliance.platform.v2.crif.schema_validator import (
    RegistrySchemaValidator,
    get_schema_validator,
)
from flowsint_crypto_compliance.platform.v2.crif.types import ConnectorLifecycle

_FORBIDDEN_MODULES = frozenset(
    {
        "flowsint_crypto_compliance.platform.v2.knowledge_graph",
        "flowsint_crypto_compliance.platform.v2.knowledge_store",
        "flowsint_crypto_compliance.platform.v2.investigation_platform",
        "flowsint_crypto_compliance.platform.v2.investigation_workspace",
    }
)


class RegistryConnector:
    """
    Wraps RFC-0007 Connector with CRIF lifecycle.
    MUST NOT mutate graph / risk / investigation — bridges handle downstream.
    """

    def __init__(
        self,
        connector: Connector,
        *,
        normalizer: RegistryNormalizer | None = None,
        validator: RegistrySchemaValidator | None = None,
    ) -> None:
        self.connector = connector
        self._normalizer = normalizer or get_registry_normalizer()
        self._validator = validator or get_schema_validator()
        self._stages: list[str] = []

    @property
    def connector_id(self) -> str:
        return self.connector.descriptor.connector_id

    @property
    def stages_completed(self) -> list[str]:
        return list(self._stages)

    async def connect(self) -> dict[str, Any]:
        result = await self.connector.connect()
        self._stages.append(ConnectorLifecycle.CONNECT.value)
        return result

    async def authenticate(self) -> dict[str, Any]:
        result = await self.connector.authenticate()
        self._stages.append(ConnectorLifecycle.AUTHENTICATE.value)
        return result

    async def collect(self, *, query: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        records = await self.connector.collect(query=query)
        self._stages.append(ConnectorLifecycle.COLLECT.value)
        return records

    def normalize(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = self._normalizer.normalize(self.connector, records)
        self._stages.append(ConnectorLifecycle.NORMALIZE.value)
        return normalized

    def validate(self, records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
        valid, errors = self._validator.validate(self.connector, records)
        self._stages.append(ConnectorLifecycle.VALIDATE.value)
        return valid, errors

    async def publish(self, *_args: Any, **_kwargs: Any) -> int:
        """CRIF Ch.18 — connector does not publish; orchestrator handles bridges."""
        self._stages.append(ConnectorLifecycle.PUBLISH.value)
        return 0

    async def shutdown(self) -> None:
        await self.connector.shutdown()
        self._stages.append(ConnectorLifecycle.SHUTDOWN.value)

    @staticmethod
    def architectural_constraints() -> dict[str, Any]:
        return {
            "forbidden": [
                "direct_knowledge_graph_mutation",
                "direct_risk_scoring",
                "direct_investigation_mutation",
                "entity_resolution_bypass",
            ],
            "forbidden_modules": sorted(_FORBIDDEN_MODULES),
            "publish_delegated_to": "orchestrator.kg_bridge + fusion_bridge + risk_bridge",
        }
