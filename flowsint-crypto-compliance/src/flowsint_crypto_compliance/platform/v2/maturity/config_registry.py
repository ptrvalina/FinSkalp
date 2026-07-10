"""Safe configuration snapshot — no secret values (Wave 5)."""

from __future__ import annotations

import os
from typing import Any

_SAFE_PREFIXES = (
    "FINSKALP_",
    "COMPLIANCE_",
    "OTEL_",
    "DATABASE_",
    "REDIS_",
    "NEO4J_",
    "CELERY_",
    "NODE_ENV",
    "ALLOWED_ORIGINS",
)

_SECRET_MARKERS = ("KEY", "SECRET", "PASSWORD", "TOKEN", "VAULT")


def _is_secret_key(name: str) -> bool:
    upper = name.upper()
    return any(marker in upper for marker in _SECRET_MARKERS)


def safe_config_snapshot() -> dict[str, Any]:
    """Expose which config keys are set without leaking values."""
    keys: dict[str, str] = {}
    for name, value in os.environ.items():
        if not any(name.startswith(p) or name == p for p in _SAFE_PREFIXES):
            continue
        if _is_secret_key(name):
            keys[name] = "set" if value.strip() else "unset"
        else:
            keys[name] = value[:120] if len(value) <= 120 else value[:117] + "..."
    return {"ok": True, "keys": keys, "count": len(keys)}
