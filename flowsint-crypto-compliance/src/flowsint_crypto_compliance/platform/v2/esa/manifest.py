"""RFC-0020 ESA v2.0 manifest."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.esa.api_protection import api_protection_manifest
from flowsint_crypto_compliance.platform.v2.esa.audit_system import audit_system_manifest
from flowsint_crypto_compliance.platform.v2.esa.authentication import authentication_manifest
from flowsint_crypto_compliance.platform.v2.esa.authorization import authorization_manifest
from flowsint_crypto_compliance.platform.v2.esa.constraints import zero_trust_constraints
from flowsint_crypto_compliance.platform.v2.esa.continuity import continuity_manifest
from flowsint_crypto_compliance.platform.v2.esa.cryptography import cryptography_manifest
from flowsint_crypto_compliance.platform.v2.esa.data_classification import data_classification_manifest
from flowsint_crypto_compliance.platform.v2.esa.evidence_security import evidence_security_manifest
from flowsint_crypto_compliance.platform.v2.esa.identity import identity_providers_manifest
from flowsint_crypto_compliance.platform.v2.esa.kg_security import kg_security_manifest
from flowsint_crypto_compliance.platform.v2.esa.sdlc import sdlc_manifest
from flowsint_crypto_compliance.platform.v2.esa.secrets import secrets_manifest
from flowsint_crypto_compliance.platform.v2.esa.security_monitoring import security_monitoring_manifest
from flowsint_crypto_compliance.platform.v2.esa.service_mesh import service_mesh_manifest
from flowsint_crypto_compliance.platform.v2.esa.siem import siem_manifest
from flowsint_crypto_compliance.platform.v2.esa.threat_model import threat_model_manifest
from flowsint_crypto_compliance.platform.v2.esa.types import DataClassification, EnterpriseRole, SecurityPrinciple
from flowsint_crypto_compliance.platform.v2.esa.vulnerability import vulnerability_manifest
from flowsint_crypto_compliance.platform.v2.events import SCHEMA_VERSION


def esa_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0020",
        "schema_version": SCHEMA_VERSION,
        "title": "Enterprise Security Architecture v2.0",
        "title_ru": "Корпоративная архитектура безопасности v2.0",
        "principle": "Zero Trust",
        "principle_ru": "Zero Trust — проверка каждого запроса, минимальные привилегии, аудит всего",
        "chapters": list(range(1, 21)),
        "security_principles": [p.value for p in SecurityPrinciple],
        "enterprise_roles": [r.value for r in EnterpriseRole],
        "data_classifications": [c.value for c in DataClassification],
        "zero_trust": zero_trust_constraints(),
        "identity": identity_providers_manifest(),
        "authentication": authentication_manifest(),
        "authorization": authorization_manifest(),
        "data_classification": data_classification_manifest(),
        "cryptography": cryptography_manifest(),
        "secrets": secrets_manifest(),
        "api_protection": api_protection_manifest(),
        "service_mesh": service_mesh_manifest(),
        "kg_security": kg_security_manifest(),
        "evidence_security": evidence_security_manifest(),
        "audit_system": audit_system_manifest(),
        "siem": siem_manifest(),
        "threat_model_summary": {
            "threat_count": threat_model_manifest()["threat_count"],
            "status_summary": threat_model_manifest()["status_summary"],
        },
        "sdlc": sdlc_manifest(),
        "vulnerability": vulnerability_manifest(),
        "monitoring": security_monitoring_manifest(),
        "continuity": continuity_manifest(),
        "api": {
            "manifest": "/api/platform/v2/esa/manifest",
            "evaluate_access": "/api/platform/v2/esa/access/evaluate",
            "audit": "/api/platform/v2/esa/audit",
            "threat_model": "/api/platform/v2/esa/threat-model",
            "monitoring": "/api/platform/v2/esa/monitoring",
            "siem": "/api/platform/v2/esa/siem",
            "data_classification": "/api/platform/v2/esa/data-classification",
        },
    }
