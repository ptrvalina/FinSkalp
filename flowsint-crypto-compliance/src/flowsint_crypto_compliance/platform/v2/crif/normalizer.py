"""RFC-0015 Ch.5 — registry normalizer."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.connectors.base import Connector
from flowsint_crypto_compliance.platform.v2.crif.types import CanonicalEntityType

_TYPE_MAP: dict[str, str] = {
    "organization": CanonicalEntityType.ORGANIZATION.value,
    "company": CanonicalEntityType.ORGANIZATION.value,
    "license": CanonicalEntityType.LICENSE.value,
    "registry_record": CanonicalEntityType.REGISTRY_RECORD.value,
    "sanction_entry": CanonicalEntityType.SANCTION_ENTRY.value,
    "sanction": CanonicalEntityType.SANCTION_ENTRY.value,
    "country": CanonicalEntityType.COUNTRY.value,
    "jurisdiction": CanonicalEntityType.JURISDICTION.value,
    "beneficial_owner": CanonicalEntityType.BENEFICIAL_OWNER.value,
    "regulator": CanonicalEntityType.REGULATOR.value,
    "compliance_rule": CanonicalEntityType.COMPLIANCE_RULE.value,
}


class RegistryNormalizer:
    """Map registry records to canonical CRIF entity types."""

    def normalize(self, connector: Connector, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        base = connector.normalize(records)
        out: list[dict[str, Any]] = []
        for rec in base:
            raw_type = str(rec.get("entity_type") or "unknown").lower()
            canonical = _TYPE_MAP.get(raw_type, CanonicalEntityType.REGISTRY_RECORD.value)
            payload = rec.get("payload") if isinstance(rec.get("payload"), dict) else rec
            out.append(
                {
                    **rec,
                    "entity_type": canonical,
                    "canonical_entity_type": canonical,
                    "source_type": str(rec.get("source_type") or connector.descriptor.connector_id),
                    "payload": {
                        **(payload or {}),
                        "original_entity_type": raw_type,
                        "connector_id": connector.descriptor.connector_id,
                    },
                }
            )
        return out


_default: RegistryNormalizer | None = None


def get_registry_normalizer() -> RegistryNormalizer:
    global _default
    if _default is None:
        _default = RegistryNormalizer()
    return _default
