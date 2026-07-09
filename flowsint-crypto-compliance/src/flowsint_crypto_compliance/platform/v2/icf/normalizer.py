"""RFC-0014 Ch.5 — pluggable normalizer."""

from __future__ import annotations

from typing import Any, Protocol

from flowsint_crypto_compliance.platform.v2.connectors.base import Connector


class Normalizer(Protocol):
    def normalize(self, connector: Connector, records: list[dict[str, Any]]) -> list[dict[str, Any]]: ...


class ConnectorNormalizer:
    """Delegates to connector default normalize()."""

    def normalize(self, connector: Connector, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return connector.normalize(records)


_default_normalizer: ConnectorNormalizer | None = None


def get_normalizer() -> ConnectorNormalizer:
    global _default_normalizer
    if _default_normalizer is None:
        _default_normalizer = ConnectorNormalizer()
    return _default_normalizer
