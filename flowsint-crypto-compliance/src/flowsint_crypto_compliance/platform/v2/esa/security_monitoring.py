"""RFC-0020 Ch.18 — security monitoring metrics."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SecurityMetrics:
    """In-memory security monitoring metrics."""

    failed_auth_count: int = 0
    role_change_count: int = 0
    api_anomaly_count: int = 0
    evidence_integrity_violations: int = 0
    access_denied_count: int = 0
    export_count: int = 0
    admin_action_count: int = 0
    ai_interaction_count: int = 0
    security_scan_count: int = 0
    by_endpoint: dict[str, int] = field(default_factory=dict)

    def record_failed_auth(self) -> None:
        self.failed_auth_count += 1

    def record_role_change(self) -> None:
        self.role_change_count += 1

    def record_api_anomaly(self, endpoint: str = "") -> None:
        self.api_anomaly_count += 1
        if endpoint:
            self.by_endpoint[endpoint] = self.by_endpoint.get(endpoint, 0) + 1

    def record_integrity_violation(self) -> None:
        self.evidence_integrity_violations += 1

    def record_access_denied(self) -> None:
        self.access_denied_count += 1

    def record_export(self) -> None:
        self.export_count += 1

    def record_admin_action(self) -> None:
        self.admin_action_count += 1

    def record_ai_interaction(self) -> None:
        self.ai_interaction_count += 1

    def record_security_scan(self) -> None:
        self.security_scan_count += 1

    def get_metrics(self) -> dict[str, Any]:
        return {
            "failed_auth_count": self.failed_auth_count,
            "role_change_count": self.role_change_count,
            "api_anomaly_count": self.api_anomaly_count,
            "evidence_integrity_violations": self.evidence_integrity_violations,
            "access_denied_count": self.access_denied_count,
            "export_count": self.export_count,
            "admin_action_count": self.admin_action_count,
            "ai_interaction_count": self.ai_interaction_count,
            "security_scan_count": self.security_scan_count,
            "by_endpoint": dict(self.by_endpoint),
        }


_metrics: SecurityMetrics | None = None


def get_security_metrics() -> SecurityMetrics:
    global _metrics
    if _metrics is None:
        _metrics = SecurityMetrics()
    return _metrics


def reset_security_metrics() -> None:
    global _metrics
    _metrics = None


class LatencyTimer:
    def __init__(self) -> None:
        self._start = 0.0
        self.elapsed_ms = 0.0

    def __enter__(self) -> "LatencyTimer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: object) -> None:
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000


def security_monitoring_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0020",
        "chapter": 18,
        "metrics": [
            "failed_auth_count",
            "role_change_count",
            "api_anomaly_count",
            "evidence_integrity_violations",
            "access_denied_count",
            "export_count",
            "admin_action_count",
            "ai_interaction_count",
        ],
        "alert_thresholds": {
            "failed_auth_per_hour": 50,
            "integrity_violations_per_day": 1,
            "role_changes_per_day": 10,
        },
        "principle_ru": "Мониторинг безопасности — failed auth, role changes, аномалии API, нарушения целостности",
    }
