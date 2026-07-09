"""RFC-0015 Ch.10 — jurisdiction intelligence per entity."""

from __future__ import annotations

from typing import Any

_JURISDICTION_META: dict[str, dict[str, Any]] = {
    "RU": {
        "name_ru": "Российская Федерация",
        "regulator": "ЦБ РФ",
        "risk_tier": "medium",
        "fatf_member": True,
    },
    "KZ": {
        "name_ru": "Казахстан",
        "regulator": "АФР РК",
        "risk_tier": "medium",
        "fatf_member": True,
    },
    "AE": {
        "name_ru": "ОАЭ",
        "regulator": "VARA / FSRA",
        "risk_tier": "low",
        "fatf_member": True,
    },
    "US": {
        "name_ru": "США",
        "regulator": "FinCEN / OFAC",
        "risk_tier": "low",
        "fatf_member": True,
    },
}


def resolve_jurisdiction(
    records: list[dict[str, Any]],
    *,
    default: str = "RU",
) -> list[dict[str, Any]]:
    """Attach jurisdiction intelligence to registry records."""
    enriched: list[dict[str, Any]] = []
    for rec in records:
        payload = rec.get("payload") if isinstance(rec.get("payload"), dict) else {}
        code = str(payload.get("jurisdiction") or default).upper()
        meta = _JURISDICTION_META.get(code, {
            "name_ru": code,
            "regulator": "unknown",
            "risk_tier": "unknown",
            "fatf_member": False,
        })
        enriched.append(
            {
                **rec,
                "jurisdiction": {
                    "code": code,
                    **meta,
                },
            }
        )
    return enriched
