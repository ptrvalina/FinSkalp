"""RFC-0015 — registry connector catalog mapping connector_ids to source categories."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.connectors.base import BaseConnector
from flowsint_crypto_compliance.platform.v2.crif.types import RegistrySourceCategory


_CONNECTOR_CATEGORIES: dict[str, RegistrySourceCategory] = {
    "registry.ofac": RegistrySourceCategory.SANCTIONS,
    "registry.sovereign": RegistrySourceCategory.GOVERNMENT,
    "registry.cis_vasp": RegistrySourceCategory.LICENSES,
    "registry.corporate": RegistrySourceCategory.CORPORATE,
}


class _RegistryDataConnector(BaseConnector):
    """Enriched registry connector for CRIF pipeline demos and tests."""

    async def connect(self) -> dict[str, Any]:
        return {"ok": True, "connector_id": self.descriptor.connector_id}

    async def authenticate(self) -> dict[str, Any]:
        return {"ok": True, "authenticated": True}

    async def health(self) -> dict[str, Any]:
        return {"ok": True, "status": "healthy", "connector_id": self.descriptor.connector_id}

    async def collect(self, *, query: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        q = query or {}
        cid = self.descriptor.connector_id
        org = str(q.get("entity_value") or q.get("organization") or q.get("name") or "Test Organization")
        reg_num = str(q.get("registration_number") or f"REG-{org[:8].upper().replace(' ', '')}")

        if cid == "registry.ofac":
            return [
                {
                    "entity_type": "sanction_entry",
                    "entity_value": org,
                    "confidence": 0.95,
                    "payload": {
                        "list": "OFAC SDN",
                        "name": org,
                        "program": "CYBER2",
                        "sanctioned": True,
                    },
                }
            ]
        if cid == "registry.sovereign":
            return [
                {
                    "entity_type": "organization",
                    "entity_value": org,
                    "confidence": 0.92,
                    "payload": {
                        "name": org,
                        "registration_number": reg_num,
                        "status": "active",
                        "jurisdiction": "RU",
                        "licenses": [{"type": "vasp", "status": "active", "number": "VASP-001"}],
                    },
                },
                {
                    "entity_type": "license",
                    "entity_value": f"VASP-001:{org}",
                    "confidence": 0.9,
                    "payload": {
                        "license_type": "vasp",
                        "status": "active",
                        "holder": org,
                        "number": "VASP-001",
                    },
                },
            ]
        if cid == "registry.cis_vasp":
            return [
                {
                    "entity_type": "license",
                    "entity_value": f"CIS-VASP:{org}",
                    "confidence": 0.88,
                    "payload": {
                        "license_type": "cis_vasp",
                        "status": q.get("license_status", "active"),
                        "holder": org,
                    },
                }
            ]
        if cid == "registry.corporate":
            return [
                {
                    "entity_type": "organization",
                    "entity_value": org,
                    "confidence": 0.85,
                    "payload": {
                        "name": org,
                        "registration_number": reg_num,
                        "status": "active",
                        "beneficial_owners": [{"name": "John Doe", "share": 0.6}],
                    },
                }
            ]
        return [
            {
                "entity_type": str(q.get("entity_type") or "registry_record"),
                "entity_value": org,
                "confidence": self.descriptor.quality.trust_level,
            }
        ]


def get_connector_category(connector_id: str) -> RegistrySourceCategory:
    return _CONNECTOR_CATEGORIES.get(connector_id, RegistrySourceCategory.CORPORATE)


def registry_connector_catalog() -> dict[str, Any]:
    connectors = []
    for connector_id, category in _CONNECTOR_CATEGORIES.items():
        connectors.append(
            {
                "connector_id": connector_id,
                "source_category": category.value,
                "factory": "_RegistryDataConnector",
            }
        )
    return {
        "rfc": "RFC-0015",
        "connectors": connectors,
        "total": len(connectors),
    }


def register_crif_registry_connectors() -> None:
    """Register enriched factories for registry connectors."""
    from flowsint_crypto_compliance.platform.v2.connectors import get_connector_registry

    reg = get_connector_registry()
    for connector_id in _CONNECTOR_CATEGORIES:
        desc = reg.get_descriptor(connector_id)
        if desc:
            reg.register(desc, _RegistryDataConnector)
