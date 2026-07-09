"""RFC-0020 ESA v2.0 — core security types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SecurityPrinciple(str, Enum):
    """RFC-0020 Ch.1 — Zero Trust principles."""

    VERIFY_EXPLICITLY = "verify_explicitly"
    LEAST_PRIVILEGE = "least_privilege"
    ASSUME_BREACH = "assume_breach"
    MICRO_SEGMENTATION = "micro_segmentation"
    CONTINUOUS_VALIDATION = "continuous_validation"
    ENCRYPT_EVERYWHERE = "encrypt_everywhere"
    AUDIT_EVERYTHING = "audit_everything"
    NO_IMPLICIT_TRUST = "no_implicit_trust"


class DataClassification(str, Enum):
    """RFC-0020 Ch.6 — data classification levels."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class EnterpriseRole(str, Enum):
    """RFC-0020 Ch.5 — enterprise security roles."""

    ANALYST = "analyst"
    SENIOR_ANALYST = "senior_analyst"
    LEAD = "lead"
    ADMIN = "admin"
    AUDITOR = "auditor"
    INTEGRATION_SERVICE = "integration_service"


class ABACAttribute(str, Enum):
    """RFC-0020 Ch.5 — ABAC attribute keys."""

    TENANT_ID = "tenant_id"
    USER_ID = "user_id"
    ROLE = "role"
    CASE_REF = "case_ref"
    INVESTIGATION_ID = "investigation_id"
    DATA_CLASSIFICATION = "data_classification"
    RESOURCE_TYPE = "resource_type"
    SOURCE_IP = "source_ip"
    MFA_VERIFIED = "mfa_verified"
    SERVICE_ACCOUNT = "service_account"


class SecurityAuditEventType(str, Enum):
    """RFC-0020 Ch.13 — security audit event categories."""

    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    ROLE_CHANGE = "role_change"
    API_ACCESS = "api_access"
    AI_INTERACTION = "ai_interaction"
    ADMIN_ACTION = "admin_action"
    ACCESS_DENIED = "access_denied"
    INTEGRITY_VIOLATION = "integrity_violation"


@dataclass
class SecurityUser:
    """Subject for access evaluation."""

    user_id: str
    role: EnterpriseRole
    tenant_id: str = ""
    mfa_verified: bool = False
    service_account: bool = False
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "role": self.role.value,
            "tenant_id": self.tenant_id,
            "mfa_verified": self.mfa_verified,
            "service_account": self.service_account,
            "attributes": dict(self.attributes),
        }


@dataclass
class SecurityResource:
    """Resource for access evaluation."""

    resource_type: str
    resource_id: str = ""
    data_classification: DataClassification = DataClassification.INTERNAL
    tenant_id: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "data_classification": self.data_classification.value,
            "tenant_id": self.tenant_id,
            "attributes": dict(self.attributes),
        }


@dataclass
class AccessDecision:
    """Result of RBAC+ABAC evaluation."""

    allowed: bool
    reason: str
    rbac_ok: bool = False
    abac_ok: bool = False
    permission: str = ""
    effective_permissions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "rbac_ok": self.rbac_ok,
            "abac_ok": self.abac_ok,
            "permission": self.permission,
            "effective_permissions": list(self.effective_permissions),
        }
