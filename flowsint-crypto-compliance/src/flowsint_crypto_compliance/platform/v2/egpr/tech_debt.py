"""RFC-0022 Ch.8 — technical debt bridge to audit doc."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flowsint_crypto_compliance.platform.v2.egpr.types import TechDebtEntry, TechDebtSeverity

_DOCS_ROOT = Path(__file__).resolve().parents[5]
_DEBT_DOC = _DOCS_ROOT / "docs/audit/technical-debt.md"

_BOOTSTRAP_DEBT: list[TechDebtEntry] = [
    TechDebtEntry("TD-C1", TechDebtSeverity.CRITICAL, "Нет единой сущности Case", "Investigation, ComplianceCase, 2× Neo4j case labels", "Расследование не entity-first", "open", "platform_core", "RFC-0002 entity consolidation"),
    TechDebtEntry("TD-C2", TechDebtSeverity.CRITICAL, "Evidence не first-class в БД", "JSONB, OsintFinding, graph in-memory", "Evidence First нарушен", "partial", "investigation", "RFC-0017 ECCF closure"),
    TechDebtEntry("TD-C3", TechDebtSeverity.CRITICAL, "compliance.py без RBAC", "require_permission на mutate routes", "—", "closed", "security", ""),
    TechDebtEntry("TD-C4", TechDebtSeverity.CRITICAL, "Цикл пакетов core ↔ crypto-compliance", "pyproject.toml обоих", "Plugin First невозможен", "open", "platform_core", "Break package cycle"),
    TechDebtEntry("TD-C5", TechDebtSeverity.CRITICAL, "Два API gateway (5001 / 8877)", "web_server.py + main.py", "API First, security drift", "partial", "api_ecosystem", "platform/v2/routes.py shared BFF"),
    TechDebtEntry("TD-S1", TechDebtSeverity.SIGNIFICANT, "Тройной plane wallet labels", "registry + entity_labels + caches", "Label duplication", "closed", "platform_core", "RFC-0002 M2 entity_label_bridge"),
    TechDebtEntry("TD-S5", TechDebtSeverity.SIGNIFICANT, "Два RBAC: investigation vs compliance", "legacy roles", "Permission drift", "closed", "security", "RFC-0009 harmonized layer"),
    TechDebtEntry("TD-M2", TechDebtSeverity.MODERATE, "KYT exposure только in-memory", "kyt module", "No persistence", "open", "compliance", "Postgres persistence"),
    TechDebtEntry("TD-L1", TechDebtSeverity.COSMETIC, "RU/EN mix в идентификаторах", "codebase-wide", "Consistency", "open", "governance", "Naming convention RFC"),
    TechDebtEntry("TD-L2", TechDebtSeverity.COSMETIC, "Version skew packages 0.1.0 vs 1.2.8", "pyproject.toml files", "Release confusion", "open", "infrastructure", "Unified semver release"),
]

_debt_store: dict[str, TechDebtEntry] = {d.id: d for d in _BOOTSTRAP_DEBT}


def _audit_doc_exists() -> bool:
    return _DEBT_DOC.is_file()


def list_tech_debt(*, severity: str | None = None) -> list[dict[str, Any]]:
    items = list(_debt_store.values())
    if severity:
        try:
            sev = TechDebtSeverity(severity)
            items = [d for d in items if d.severity == sev]
        except ValueError:
            pass
    return [d.to_dict() for d in items]


def get_tech_debt_item(debt_id: str) -> dict[str, Any] | None:
    entry = _debt_store.get(debt_id.upper())
    return entry.to_dict() if entry else None


def update_tech_debt_plan(debt_id: str, *, owner: str, plan: str) -> dict[str, Any]:
    entry = _debt_store.get(debt_id.upper())
    if entry is None:
        return {"ok": False, "error": "debt_not_found"}
    entry.owner = owner
    entry.plan = plan
    return {"ok": True, "item": entry.to_dict()}


def tech_debt_manifest() -> dict[str, Any]:
    items = list_tech_debt()
    by_severity = {s.value: sum(1 for i in items if i["severity"] == s.value) for s in TechDebtSeverity}
    open_count = sum(1 for i in items if i["status"] in ("open", "partial"))
    return {
        "rfc": "RFC-0022",
        "chapter": 8,
        "source": "docs/audit/technical-debt.md",
        "source_exists": _audit_doc_exists(),
        "total": len(items),
        "open_count": open_count,
        "by_severity": by_severity,
        "items": items,
        "principle_ru": "Технический долг — прозрачный реестр с severity, owner и планом",
    }
