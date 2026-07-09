"""RFC-0020 Ch.3 — identity providers manifest."""

from __future__ import annotations

from typing import Any


def identity_providers_manifest() -> dict[str, Any]:
    """Supported identity provider configurations."""
    return {
        "rfc": "RFC-0020",
        "chapter": 3,
        "providers": {
            "ldap": {
                "enabled": False,
                "protocol": "LDAP",
                "bind_dn_template": "cn={username},ou=users,dc=flowsint,dc=local",
                "group_attribute": "memberOf",
                "role_mapping": {
                    "cn=analysts": "analyst",
                    "cn=senior-analysts": "senior_analyst",
                    "cn=leads": "lead",
                    "cn=admins": "admin",
                    "cn=auditors": "auditor",
                },
                "technical_debt": "TD-ESA-1",
            },
            "oidc": {
                "enabled": False,
                "issuer": "https://auth.flowsint.local/realms/finskalp",
                "client_id": "finskalp-platform",
                "scopes": ["openid", "profile", "email", "groups"],
                "role_claim": "groups",
                "technical_debt": "TD-ESA-1",
            },
            "saml": {
                "enabled": False,
                "entity_id": "urn:flowsint:finskalp",
                "sso_url": "https://idp.flowsint.local/saml/sso",
                "attribute_mapping": {
                    "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
                    "role": "http://schemas.flowsint.com/claims/role",
                },
                "technical_debt": "TD-ESA-1",
            },
            "local": {
                "enabled": True,
                "store": "flowsint_core Profile + ComplianceUserRole",
                "password_policy": {
                    "min_length": 12,
                    "require_uppercase": True,
                    "require_lowercase": True,
                    "require_digit": True,
                    "require_special": True,
                    "max_age_days": 90,
                },
            },
        },
        "default_provider": "local",
        "principle_ru": "Единая идентификация — LDAP/OIDC/SAML/локальные учётные записи через единый манифест",
    }
