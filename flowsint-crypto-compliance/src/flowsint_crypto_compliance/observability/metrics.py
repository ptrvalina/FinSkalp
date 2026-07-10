"""Prometheus metrics for compliance module."""

from __future__ import annotations

from prometheus_client import Counter, Histogram, generate_latest

COMPLIANCE_FUSION_TOTAL = Counter(
    "compliance_fusion_total",
    "OSINT fusion runs",
    ["status"],
)
COMPLIANCE_WALLET_SCREEN_TOTAL = Counter(
    "compliance_wallet_screen_total",
    "Wallet screening requests",
    ["risk_level"],
)
COMPLIANCE_REGISTRY_IMPORT_TOTAL = Counter(
    "compliance_registry_import_total",
    "Registry label imports",
    ["format"],
)
COMPLIANCE_FUSION_DURATION = Histogram(
    "compliance_fusion_duration_seconds",
    "Fusion wall time",
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60),
)
COMPLIANCE_BATCH_SCREEN_TOTAL = Counter(
    "compliance_batch_screen_total",
    "Batch screening jobs",
    ["status"],
)
COMPLIANCE_WATCHLIST_HITS = Counter(
    "compliance_watchlist_hits_total",
    "Watchlist sanction hits",
)
COMPLIANCE_WEBHOOK_INGEST_TOTAL = Counter(
    "compliance_webhook_ingest_total",
    "Inbound bank webhook ingests",
    ["bank_id"],
)
COMPLIANCE_SLA_BREACH_TOTAL = Counter(
    "compliance_sla_breach_total",
    "Case SLA breaches detected",
)
IDOO_HEALTH_PROBE_TOTAL = Counter(
    "idoo_health_probe_total",
    "IDOO infrastructure health probes",
    ["service", "status", "mode"],
)


def record_idoo_health_probe(*, service: str, status: str, mode: str) -> None:
    IDOO_HEALTH_PROBE_TOTAL.labels(service=service, status=status, mode=mode).inc()


def metrics_payload() -> bytes:
    return generate_latest()
