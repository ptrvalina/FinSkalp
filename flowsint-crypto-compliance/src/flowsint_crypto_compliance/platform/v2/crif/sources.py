"""RFC-0015 Ch.3 — registry source category catalog."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.crif.types import RegistrySourceCategory


_CATALOG: dict[RegistrySourceCategory, dict[str, Any]] = {
    RegistrySourceCategory.GOVERNMENT: {
        "title_ru": "Государственные реестры",
        "description_ru": "Официальные государственные регистры юридических лиц",
        "formats": ["registry", "filing", "public_list"],
        "examples": ["registry.sovereign"],
    },
    RegistrySourceCategory.SANCTIONS: {
        "title_ru": "Санкционные списки",
        "description_ru": "OFAC, UN, EU и национальные санкционные перечни",
        "formats": ["sanction_entry", "sdn", "consolidated_list"],
        "examples": ["registry.ofac"],
    },
    RegistrySourceCategory.LICENSES: {
        "title_ru": "Лицензии и разрешения",
        "description_ru": "VASP, финансовые и крипто-лицензии",
        "formats": ["license", "permit", "authorization"],
        "examples": ["registry.cis_vasp"],
    },
    RegistrySourceCategory.CORPORATE: {
        "title_ru": "Корпоративные справочники",
        "description_ru": "Публичные корпоративные данные и бенефициары",
        "formats": ["company", "ubo", "filing"],
        "examples": ["registry.corporate"],
    },
}


def registry_source_catalog() -> dict[str, Any]:
    categories = []
    for cat in RegistrySourceCategory:
        meta = dict(_CATALOG.get(cat, {}))
        meta["id"] = cat.value
        categories.append(meta)
    return {
        "rfc": "RFC-0015",
        "chapter": 3,
        "categories": categories,
    }


def resolve_registry_category(category: RegistrySourceCategory | str) -> RegistrySourceCategory:
    if isinstance(category, str):
        try:
            return RegistrySourceCategory(category)
        except ValueError:
            return RegistrySourceCategory.CORPORATE
    return category
