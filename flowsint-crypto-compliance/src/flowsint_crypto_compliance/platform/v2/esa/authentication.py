"""RFC-0020 Ch.4 — authentication methods manifest."""

from __future__ import annotations

from typing import Any


def authentication_manifest() -> dict[str, Any]:
    """Authentication methods and MFA policy."""
    return {
        "rfc": "RFC-0020",
        "chapter": 4,
        "methods": {
            "password": {
                "enabled": True,
                "mfa_required": False,
                "lockout_after_attempts": 5,
                "lockout_duration_seconds": 900,
            },
            "mfa_totp": {
                "enabled": True,
                "issuer": "FinSkalp",
                "algorithm": "SHA1",
                "digits": 6,
                "period_seconds": 30,
            },
            "fido2": {
                "enabled": False,
                "attestation": "direct",
                "user_verification": "required",
                "technical_debt": "TD-ESA-5",
            },
            "jwt": {
                "enabled": True,
                "algorithm": "HS256",
                "issuer": "flowsint",
                "audience": "platform-v2",
                "ttl_seconds": 3600,
                "refresh_ttl_seconds": 86_400,
            },
            "service_accounts": {
                "enabled": True,
                "auth_method": "api_key",
                "header": "X-API-Key",
                "roles": ["integration_service"],
                "rotation_days": 90,
            },
        },
        "require_mfa_for_admin": True,
        "session": {
            "idle_timeout_seconds": 1800,
            "absolute_timeout_seconds": 28_800,
            "concurrent_sessions_max": 3,
        },
        "principle_ru": "Сильная аутентификация — MFA обязателен для администраторов",
    }


def admin_requires_mfa(role: str, *, mfa_verified: bool) -> bool:
    """Enforce require_mfa_for_admin policy."""
    manifest = authentication_manifest()
    if not manifest["require_mfa_for_admin"]:
        return True
    if role in ("admin", "lead"):
        return mfa_verified
    return True
