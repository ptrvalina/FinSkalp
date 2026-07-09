"""
Политика легальных источников OSINT Scalpel (FinSkalp / Росфинмониторинг).

Только: публичные API, open data, официальные реестры, voluntarily public profiles.
Запрещено: слитые БД, дампы паролей/переписок, украденные ПДн.
"""

from __future__ import annotations

from typing import Final

# Типы источников, которые НЕ допускаются в production-runtime
BLOCKED_SOURCE_TYPES: Final[frozenset[str]] = frozenset(
    {
        "leak",
        "paste_dump",
        "breach_db",
        "credential_dump",
        "stolen_pii",
    }
)

ALLOWED_SOURCE_CATEGORIES: Final[list[dict[str, str]]] = [
    {
        "id": "onchain_public",
        "title_ru": "Публичный блокчейн",
        "legal_basis_ru": "On-chain данные общедоступны по определению",
    },
    {
        "id": "sanctions_open",
        "title_ru": "Санкционные списки open data",
        "legal_basis_ru": "OpenSanctions, OFAC SDN (US Treasury), EU/UN consolidated lists",
    },
    {
        "id": "username_public",
        "title_ru": "Публичные профили",
        "legal_basis_ru": "Maigret/Sherlock — проверка URL-паттернов, без скачивания приватных данных",
    },
    {
        "id": "abuse_crowdsource",
        "title_ru": "Краудсорс репорты abuse",
        "legal_basis_ru": "Chainabuse, BitcoinAbuse — добровольные репорты жертв",
    },
    {
        "id": "darknet_index",
        "title_ru": "Индекс Ahmia",
        "legal_basis_ru": "Только официальный clearnet-индекс .onion (без краулинга закрытых форумов)",
    },
    {
        "id": "vasp_registry",
        "title_ru": "Официальные реестры VASP",
        "legal_basis_ru": "ЦБ РФ, NAPP, AFSA, ПВТ, FATF",
    },
    {
        "id": "enforcement_public",
        "title_ru": "Публичные enforcement-материалы",
        "legal_basis_ru": "Пресс-релизы DOJ/Europol/Interpol, официальные seizure notices",
    },
    {
        "id": "dns_rdap",
        "title_ru": "RDAP/WHOIS",
        "legal_basis_ru": "Публичные записи регистраторов доменов",
    },
]


def is_blocked_source_type(source_type: str) -> bool:
    return source_type in BLOCKED_SOURCE_TYPES


def filter_legal_hits(hits: list) -> tuple[list, list[dict]]:
    """Отсеивает упоминания из запрещённых категорий источников."""
    kept, rejected = [], []
    for h in hits:
        st = getattr(h, "source_type", "") or (h.get("source_type") if isinstance(h, dict) else "")
        if is_blocked_source_type(st):
            rejected.append({"reason": "blocked_source_type", "source_type": st})
            continue
        kept.append(h)
    return kept, rejected
