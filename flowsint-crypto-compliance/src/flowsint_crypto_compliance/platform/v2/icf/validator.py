"""RFC-0014 Ch.3 — pluggable validator."""

from __future__ import annotations

from typing import Any, Protocol

from flowsint_crypto_compliance.platform.v2.connectors.base import Connector


class Validator(Protocol):
    def validate(
        self, connector: Connector, records: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[str]]: ...


class ConnectorValidator:
    """Delegates to connector default validate()."""

    def validate(
        self, connector: Connector, records: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[str]]:
        return connector.validate(records)


_default_validator: ConnectorValidator | None = None


def get_validator() -> ConnectorValidator:
    global _default_validator
    if _default_validator is None:
        _default_validator = ConnectorValidator()
    return _default_validator
