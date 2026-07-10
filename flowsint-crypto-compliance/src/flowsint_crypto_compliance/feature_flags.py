"""Additive feature-flag registry for evolutionary hardening.

Design principles (see docs/audit/architecture-hardening-plan.md):

* **Additive only** — every flag defaults to the *legacy* behaviour. When a flag
  is unset (or set to a falsy value) the platform behaves exactly as before, so
  a flag is its own rollback switch.
* **No new API** — flags are resolved from environment variables, mirroring the
  existing ``COMPLIANCE_COMBAT_MODE`` / ``FINSKALP_ENTITY_STORE`` conventions
  (see ``demo/combat_mode.py``). Nothing here changes RFCs, routes or services.
* **Observable** — reads are counted and the current snapshot is exposed via
  :func:`flag_snapshot` so health / observability endpoints can surface state.

Rollback for any capability guarded by a flag: unset the env var (or set to
``0``). No migration or redeploy of code is required.
"""

from __future__ import annotations

import logging
import os
import threading

logger = logging.getLogger(__name__)

_TRUE = {"1", "true", "yes", "on", "enabled"}
_FALSE = {"0", "false", "no", "off", "disabled", ""}

# Registry: flag name -> (env var, default). Defaults MUST preserve legacy
# behaviour (typically ``False``) so enabling is always an opt-in.
_FLAGS: dict[str, tuple[str, bool]] = {
    # Wave 1 — enterprise report sections (optional, additive template blocks).
    "enterprise_report_sections": ("FINSKALP_ENTERPRISE_REPORT_SECTIONS", False),
    # Wave 2 — ECCF Postgres WORM persistence + hash-chained audit.
    "eccf_postgres_persistence": ("FINSKALP_ECCF_POSTGRES_PERSISTENCE", False),
    # Wave 4 — IDOO real infra health probes (postgres/redis/neo4j/celery/api).
    "idoo_real_health_probes": ("FINSKALP_IDOO_REAL_HEALTH_PROBES", False),
    # Wave 4 — expose last local backup run on /idoo/backup (additive ``runtime`` key).
    "idoo_backup_runner": ("FINSKALP_IDOO_BACKUP_RUNNER", False),
    # Wave 4 — enable OTLP tracing without requiring OTEL_EXPORTER_OTLP_ENDPOINT.
    "otel_tracing": ("FINSKALP_OTEL_ENABLED", False),
    # Wave 5 — ESA security audit persistence in Postgres.
    "esa_postgres_audit": ("FINSKALP_ESA_POSTGRES_AUDIT", False),
    # Wave 5 — maturity extended CI test gate marker.
    "maturity_extended_ci": ("FINSKALP_MATURITY_EXTENDED_CI", False),
    # Wave 5 — workspace full panels (reports/wallets/alert center).
    "workspace_full_panels": ("FINSKALP_WORKSPACE_FULL_PANELS", False),
}

_lock = threading.Lock()
_read_counts: dict[str, int] = {}
_enabled_counts: dict[str, int] = {}


def _coerce(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return default if value == "" else False
    # Unknown token: fail safe to the legacy default and warn once.
    logger.warning("feature_flag: unrecognised value %r, using default %s", raw, default)
    return default


def is_enabled(name: str, *, default: bool | None = None) -> bool:
    """Resolve a feature flag. Unknown flags default to ``False`` (legacy)."""
    env_var, registered_default = _FLAGS.get(name, (None, False))
    effective_default = registered_default if default is None else default
    if env_var is None:
        # Ad-hoc flag: derive a conventional env var name.
        env_var = "FINSKALP_" + name.upper()
    result = _coerce(os.getenv(env_var), effective_default)
    with _lock:
        _read_counts[name] = _read_counts.get(name, 0) + 1
        if result:
            _enabled_counts[name] = _enabled_counts.get(name, 0) + 1
    return result


def flag_snapshot() -> dict[str, dict[str, object]]:
    """Observability helper: current state + read metrics for every known flag."""
    with _lock:
        reads = dict(_read_counts)
        enabled = dict(_enabled_counts)
    snapshot: dict[str, dict[str, object]] = {}
    for name, (env_var, default) in _FLAGS.items():
        snapshot[name] = {
            "env_var": env_var,
            "default": default,
            "enabled": is_enabled(name),
            "read_count": reads.get(name, 0),
            "enabled_count": enabled.get(name, 0),
        }
    return snapshot


# --- Named helpers (typed call sites; easier to grep than string keys) --------


def enterprise_report_sections_enabled() -> bool:
    """Wave 1: render optional enterprise report sections when enabled."""
    return is_enabled("enterprise_report_sections")


def eccf_postgres_persistence_enabled() -> bool:
    """Wave 2: persist ECCF evidence + audit trail in Postgres (WORM + hash chain)."""
    return is_enabled("eccf_postgres_persistence")


def idoo_real_health_probes_enabled() -> bool:
    """Wave 4: run real IDOO service health probes instead of stub."""
    return is_enabled("idoo_real_health_probes")


def idoo_backup_runner_enabled() -> bool:
    """Wave 4: attach backup runner runtime status to IDOO backup manifest."""
    return is_enabled("idoo_backup_runner")


def otel_tracing_enabled() -> bool:
    """Wave 4: opt-in OpenTelemetry without mandatory OTLP endpoint env."""
    return is_enabled("otel_tracing")


def esa_postgres_audit_enabled() -> bool:
    """Wave 5: persist ESA security audit log in Postgres."""
    return is_enabled("esa_postgres_audit")


def workspace_full_panels_enabled() -> bool:
    """Wave 5: enable full workspace panels (reports, wallets, alert center)."""
    return is_enabled("workspace_full_panels")
