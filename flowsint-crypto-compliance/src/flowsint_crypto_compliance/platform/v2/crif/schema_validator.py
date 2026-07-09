"""RFC-0015 Ch.5 — schema validator for registry records."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.connectors.base import Connector
from flowsint_crypto_compliance.platform.v2.crif.types import CanonicalEntityType

_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    CanonicalEntityType.ORGANIZATION.value: ("entity_value",),
    CanonicalEntityType.LICENSE.value: ("entity_value",),
    CanonicalEntityType.REGISTRY_RECORD.value: ("entity_value",),
    CanonicalEntityType.SANCTION_ENTRY.value: ("entity_value",),
    CanonicalEntityType.COUNTRY.value: ("entity_value",),
    CanonicalEntityType.JURISDICTION.value: ("entity_value",),
    CanonicalEntityType.BENEFICIAL_OWNER.value: ("entity_value",),
    CanonicalEntityType.REGULATOR.value: ("entity_value",),
    CanonicalEntityType.COMPLIANCE_RULE.value: ("entity_value",),
}


class RegistrySchemaValidator:
    """Validate canonical schema fields — delegates base validation to connector."""

    def validate(
        self, connector: Connector, records: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[str]]:
        valid, errors = connector.validate(records)
        schema_valid: list[dict[str, Any]] = []
        for i, rec in enumerate(valid):
            et = str(rec.get("entity_type") or rec.get("canonical_entity_type") or "")
            required = _REQUIRED_FIELDS.get(et, ("entity_value",))
            missing = [f for f in required if not rec.get(f)]
            if missing:
                errors.append(f"row {i}: schema missing fields {missing} for {et}")
                continue
            conf = rec.get("confidence")
            if conf is not None:
                try:
                    cf = float(conf)
                    if not 0.0 <= cf <= 1.0:
                        errors.append(f"row {i}: confidence out of range")
                        continue
                except (TypeError, ValueError):
                    errors.append(f"row {i}: invalid confidence")
                    continue
            schema_valid.append(rec)
        return schema_valid, errors


_default: RegistrySchemaValidator | None = None


def get_schema_validator() -> RegistrySchemaValidator:
    global _default
    if _default is None:
        _default = RegistrySchemaValidator()
    return _default
