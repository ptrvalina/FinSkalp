"""Реестр реальных VASP/операторов цифровых активов стран СНГ (публичные регуляторные источники)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from flowsint_crypto_compliance.cis.coverage import CISJurisdiction

_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "data" / "cis_vasp_registry.json"

# Все юрисдикции СНГ из coverage — реестр должен иметь покрытие по каждой
_CIS_CODES = {j.value for j in CISJurisdiction}


def _normalize_entry(raw: dict[str, Any]) -> dict[str, Any]:
    """Приводим к формату EXCHANGERS_REGISTRY для обратной совместимости UI/API."""
    service_types = raw.get("service_types") or []
    channel = raw.get("channel") or "licensed_domestic_vex"
    return {
        "id": raw["id"],
        "label_ru": raw["legal_name_ru"],
        "legal_name_ru": raw["legal_name_ru"],
        "jurisdiction": raw["jurisdiction"],
        "regulator": raw.get("regulator", ""),
            "license_type": raw.get("license_type", ""),
            "license_ref": raw.get("license_ref"),
            "service_types": service_types,
        "channel": channel,
        "region": raw.get("region", ""),
        "risk": raw.get("risk", "low"),
        "exposure_usd_m": raw.get("exposure_usd_m"),
        "wallets": raw.get("wallets"),
        "sar_linked": raw.get("sar_linked", 0),
        "status": raw.get("status", "active"),
        "licensed": bool(raw.get("licensed", True)),
        "registry_source": raw.get("registry_source"),
        "website": raw.get("website"),
            "registry_ref": raw.get("registry_ref"),
            "known_wallets": list(raw.get("known_wallets") or []),
        }


@lru_cache(maxsize=1)
def load_cis_vasp_registry() -> list[dict[str, Any]]:
    with _REGISTRY_PATH.open(encoding="utf-8") as f:
        payload = json.load(f)
    entries = [_normalize_entry(row) for row in payload.get("entries", [])]
    if not entries:
        raise ValueError(f"CIS VASP registry is empty: {_REGISTRY_PATH}")
    return entries


def registry_metadata() -> dict[str, Any]:
    with _REGISTRY_PATH.open(encoding="utf-8") as f:
        payload = json.load(f)
    entries = load_cis_vasp_registry()
    by_jurisdiction: dict[str, int] = {}
    licensed = 0
    for e in entries:
        code = e["jurisdiction"]
        by_jurisdiction[code] = by_jurisdiction.get(code, 0) + 1
        if e.get("licensed"):
            licensed += 1
    missing = sorted(_CIS_CODES - set(by_jurisdiction))
    return {
        "schema_version": payload.get("schema_version"),
        "updated_at": payload.get("updated_at"),
        "description_ru": payload.get("description_ru"),
        "total": len(entries),
        "licensed_count": licensed,
        "by_jurisdiction": by_jurisdiction,
        "jurisdictions_covered": len(by_jurisdiction),
        "jurisdictions_missing": missing,
        "source_file": str(_REGISTRY_PATH.name),
    }


def list_by_jurisdiction(jurisdiction: str) -> list[dict[str, Any]]:
    code = jurisdiction.upper()
    return [e for e in load_cis_vasp_registry() if e["jurisdiction"] == code]


def lookup_vasp(vasp_id: str) -> dict[str, Any] | None:
    for e in load_cis_vasp_registry():
        if e["id"] == vasp_id:
            return e
    return None


def match_vasp_for_address(address: str, chain: str) -> dict[str, Any] | None:
    """Сопоставление только по явно известным кошелькам VASP (без эвристик по хешу)."""
    norm = address.lower() if chain == "eth" else address
    for entry in load_cis_vasp_registry():
        for wallet in entry.get("known_wallets") or []:
            w = wallet.lower() if chain == "eth" else wallet
            if w == norm:
                return entry
    return None


def lookup_vasp_by_wallet(address: str, chain: str) -> dict[str, Any] | None:
    return match_vasp_for_address(address, chain)
