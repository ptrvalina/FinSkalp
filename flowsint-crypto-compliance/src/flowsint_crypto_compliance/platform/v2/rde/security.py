"""RFC-0016 Ch.16 — security requirements manifest."""

from __future__ import annotations

from typing import Any


def rde_security_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0016",
        "chapter": 16,
        "requirements": [
            "read_only_subsystem_access",
            "access_logging",
            "rate_limiting",
            "input_validation",
            "service_isolation",
            "analyst_decision_boundary",
            "rule_version_audit",
        ],
        "implementation": {
            "isolation": "orchestrator forbidden_modules — no direct KG/evidence mutation",
            "logging": "platform event bus + rde monitoring metrics",
            "rate_limit": "rde.monitoring + celery beat 900s",
            "input_validation": "normalizer + constraints enforcement",
            "decision_boundary": "recommendations only — auto_decision=False",
            "rule_audit": "rules_engine version history + rollback stubs",
        },
    }
