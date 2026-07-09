"""RFC-0015 Ch.6 — organization compliance checks."""

from __future__ import annotations

from typing import Any


def run_organization_checks(
    records: list[dict[str, Any]],
    *,
    organization_key: str,
    cross_source_records: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Ch.6 checks: exists, registration, licenses, restrictions, status changes, cross-source matches.
    """
    org_records = [
        r
        for r in records
        if str(r.get("entity_type")) in ("Organization", "organization")
        or str(r.get("entity_value", "")).lower() == organization_key.lower()
    ]
    license_records = [r for r in records if str(r.get("entity_type")) in ("License", "license")]
    sanction_records = [r for r in records if str(r.get("entity_type")) in ("SanctionEntry", "sanction_entry")]

    checks: list[dict[str, Any]] = []

    checks.append(
        {
            "check_id": "org_exists",
            "check_type": "exists",
            "passed": bool(org_records),
            "severity": "high" if not org_records else "info",
            "message_ru": "Организация найдена в реестре" if org_records else "Организация не найдена",
            "organization_key": organization_key,
        }
    )

    reg_nums = []
    for r in org_records:
        payload = r.get("payload") if isinstance(r.get("payload"), dict) else {}
        if payload.get("registration_number"):
            reg_nums.append(payload["registration_number"])
    checks.append(
        {
            "check_id": "registration_valid",
            "check_type": "registration",
            "passed": bool(reg_nums),
            "severity": "medium" if not reg_nums else "info",
            "message_ru": "Регистрационный номер подтверждён" if reg_nums else "Регистрационный номер отсутствует",
            "registration_numbers": reg_nums,
        }
    )

    active_licenses = []
    for r in license_records:
        payload = r.get("payload") if isinstance(r.get("payload"), dict) else {}
        if str(payload.get("status", "active")).lower() == "active":
            active_licenses.append(r.get("entity_value"))
    checks.append(
        {
            "check_id": "licenses_active",
            "check_type": "licenses",
            "passed": bool(active_licenses),
            "severity": "medium" if not active_licenses else "info",
            "message_ru": f"Активных лицензий: {len(active_licenses)}",
            "active_licenses": active_licenses,
        }
    )

    restrictions = [r for r in sanction_records if (r.get("payload") or {}).get("sanctioned")]
    checks.append(
        {
            "check_id": "restrictions",
            "check_type": "restrictions",
            "passed": not restrictions,
            "severity": "critical" if restrictions else "info",
            "message_ru": "Обнаружены санкционные ограничения" if restrictions else "Ограничения не обнаружены",
            "restriction_count": len(restrictions),
        }
    )

    statuses = set()
    for r in org_records:
        payload = r.get("payload") if isinstance(r.get("payload"), dict) else {}
        if payload.get("status"):
            statuses.add(str(payload["status"]).lower())
    checks.append(
        {
            "check_id": "status_current",
            "check_type": "status_changes",
            "passed": "dissolved" not in statuses and "revoked" not in statuses,
            "severity": "high" if "dissolved" in statuses or "revoked" in statuses else "info",
            "message_ru": f"Статус: {', '.join(statuses) or 'неизвестен'}",
            "statuses": list(statuses),
        }
    )

    cross_matches = 0
    if cross_source_records:
        org_names = {str(r.get("entity_value", "")).lower() for r in org_records}
        for other in cross_source_records:
            if str(other.get("entity_value", "")).lower() in org_names:
                cross_matches += 1
    checks.append(
        {
            "check_id": "cross_source_match",
            "check_type": "cross_source_matches",
            "passed": cross_matches > 0 if cross_source_records else True,
            "severity": "medium" if cross_source_records and cross_matches == 0 else "info",
            "message_ru": f"Перекрёстных совпадений: {cross_matches}",
            "match_count": cross_matches,
        }
    )

    return checks
