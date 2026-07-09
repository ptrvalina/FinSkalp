"""Runtime integration status for Platform v2 live wiring."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.demo.combat_mode import is_combat_mode
from flowsint_crypto_compliance.platform.v2.entity_store_mode import entity_store_mode

_COMPONENT_ORDER = [
    "blockchain",
    "ICF",
    "CRIF",
    "RDE",
    "ECCF",
    "EIA",
    "ASPP",
    "ESA",
    "IDOO",
    "EGPR",
    "KG",
    "event bus",
    "celery",
]


def _has_env(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def _row(component: str, status: str, real_data: str, needs_external: list[str]) -> dict[str, Any]:
    return {
        "component": component,
        "status": status,
        "real_data": real_data,
        "needs_external": needs_external,
    }


def _status_rows() -> list[dict[str, Any]]:
    combat = is_combat_mode()
    store_mode = entity_store_mode()
    has_db = _has_env("DATABASE_URL")
    has_trongrid = _has_env("TRONGRID_API_KEY")
    has_openai = _has_env("OPENAI_API_KEY")
    has_celery = _has_env("CELERY_BROKER_URL") or _has_env("REDIS_URL")
    persistent_kg = store_mode == "postgres" and has_db

    blockchain_status = "working" if combat and has_trongrid else "partial" if combat else "working"
    blockchain_real = "yes" if combat and has_trongrid else "partial" if combat else "no"

    kg_status = "working" if persistent_kg else "partial"
    kg_real = "yes" if persistent_kg else "partial"

    celery_status = "working" if has_celery else "partial"
    celery_real = "yes" if has_celery else "no"

    eia_status = "working" if has_openai else "partial"
    eia_real = "yes" if has_openai else "partial"

    return [
        _row(
            "blockchain",
            blockchain_status,
            blockchain_real,
            ["TRONGRID_API_KEY", "public blockchain RPC/explorer APIs", "DATABASE_URL"],
        ),
        _row(
            "ICF",
            "working",
            "partial" if combat else "no",
            ["real connector APIs / data providers"],
        ),
        _row(
            "CRIF",
            "partial",
            "partial",
            ["official registries", "sanctions feeds", "registry APIs"],
        ),
        _row(
            "RDE",
            "working",
            "partial" if combat else "no",
            ["blockchain intelligence", "CRIF registries", "DATABASE_URL"],
        ),
        _row(
            "ECCF",
            "working",
            "partial",
            ["persistent evidence storage backend"],
        ),
        _row(
            "EIA",
            eia_status,
            eia_real,
            ["OPENAI_API_KEY"],
        ),
        _row(
            "ASPP",
            "working",
            "no",
            ["external plugin/webhook consumers"],
        ),
        _row(
            "ESA",
            "working",
            "no",
            ["IdP / SIEM / secret manager"],
        ),
        _row(
            "IDOO",
            "working",
            "partial",
            ["Postgres", "Redis", "Neo4j", "Celery workers"],
        ),
        _row(
            "EGPR",
            "working",
            "no",
            ["RFC/ADR external workflows if needed"],
        ),
        _row(
            "KG",
            kg_status,
            kg_real,
            ["DATABASE_URL"] if not persistent_kg else [],
        ),
        _row(
            "event bus",
            "working",
            "yes",
            ["REDIS_URL"] if not _has_env("REDIS_URL") else [],
        ),
        _row(
            "celery",
            celery_status,
            celery_real,
            ["CELERY_BROKER_URL or REDIS_URL", "running Celery worker"],
        ),
    ]


def get_integration_status() -> dict[str, Any]:
    """Return current platform integration readiness for live testing."""
    items = _status_rows()
    return {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "combat_mode": is_combat_mode(),
        "entity_store": entity_store_mode(),
        "items": sorted(items, key=lambda row: _COMPONENT_ORDER.index(row["component"])),
    }


def render_status_markdown_table(status: dict[str, Any] | None = None) -> str:
    """Render Russian markdown table for docs and reports."""
    payload = status or get_integration_status()
    lines = [
        "| Компонент | Статус | Реальные данные | Что подключить |",
        "| --- | --- | --- | --- |",
    ]
    for item in payload.get("items", []):
        needs = ", ".join(item.get("needs_external") or []) or "—"
        lines.append(
            f"| {item['component']} | {item['status']} | {item['real_data']} | {needs} |"
        )
    return "\n".join(lines)
