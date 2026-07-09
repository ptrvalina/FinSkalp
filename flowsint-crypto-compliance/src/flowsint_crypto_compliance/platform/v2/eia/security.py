"""RFC-0018 Ch.15 — security manifest, audit log, PII guard."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


_audit_log: list[dict[str, Any]] = []


def eia_security_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0018",
        "chapter": 15,
        "requirements": [
            "audit_log",
            "pii_guard",
            "prompt_injection_guard",
            "access_logging",
            "no_auto_decision",
            "read_only_subsystems",
        ],
        "pii_guard": {
            "enabled": True,
            "redact_fields": ["email", "phone", "passport", "inn", "snils"],
            "mask_in_prompts": True,
        },
        "prompt_injection_guard": {
            "enabled": True,
            "strip_system_override": True,
        },
        "implementation": {
            "audit": "eia.security.append_audit_entry",
            "pii": "context_engine masks PII before prompt render",
            "access": "gateway routes require auth dependency",
        },
    }


def append_audit_entry(
    *,
    action: str,
    actor: str,
    case_ref: str | None = None,
    task_type: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entry = {
        "action": action,
        "actor": actor,
        "case_ref": case_ref,
        "task_type": task_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": details or {},
    }
    _audit_log.append(entry)
    return entry


def get_audit_log(*, limit: int = 100) -> list[dict[str, Any]]:
    return list(_audit_log[-limit:])


def redact_pii(text: str) -> str:
    """Basic PII masking for prompt safety."""
    import re

    text = re.sub(r"\b[\w.-]+@[\w.-]+\.\w+\b", "[EMAIL]", text)
    text = re.sub(r"\b\+?\d[\d\s\-()]{8,}\d\b", "[PHONE]", text)
    text = re.sub(r"\b\d{10,12}\b", "[ID]", text)
    return text


def reset_audit_log() -> None:
    global _audit_log
    _audit_log = []
