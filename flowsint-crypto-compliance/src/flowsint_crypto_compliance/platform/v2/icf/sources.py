"""RFC-0014 Ch.2 — source category registry."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.connectors.types import ConnectorCategory
from flowsint_crypto_compliance.platform.v2.icf.types import SourceCategory

_CONNECTOR_TO_ICF: dict[ConnectorCategory, SourceCategory] = {
    ConnectorCategory.BLOCKCHAIN: SourceCategory.BLOCKCHAIN,
    ConnectorCategory.BLOCKCHAIN_INTELLIGENCE: SourceCategory.BLOCKCHAIN,
    ConnectorCategory.PUBLIC_EXPLORER: SourceCategory.BLOCKCHAIN,
    ConnectorCategory.REGISTRY: SourceCategory.GOVERNMENT_REGISTRIES,
    ConnectorCategory.OSINT: SourceCategory.PUBLIC_WEB,
    ConnectorCategory.DOCUMENT: SourceCategory.DOCUMENTS,
}

_ICF_CATALOG: dict[SourceCategory, dict[str, Any]] = {
    SourceCategory.BLOCKCHAIN: {
        "title_ru": "Блокчейн",
        "description_ru": "Публичные сети и блокчейн-эксплореры",
        "formats": ["address", "transaction", "block"],
    },
    SourceCategory.PUBLIC_WEB: {
        "title_ru": "Публичный веб",
        "description_ru": "Открытые сайты, публичные API",
        "formats": ["html", "json", "api"],
    },
    SourceCategory.NEWS: {
        "title_ru": "Новости",
        "description_ru": "Новостные публикации, пресс-релизы",
        "formats": ["article", "rss", "announcement"],
    },
    SourceCategory.GOVERNMENT_REGISTRIES: {
        "title_ru": "Государственные реестры",
        "description_ru": "Лицензии, публичные списки",
        "formats": ["registry", "license", "public_list"],
    },
    SourceCategory.CORPORATE_DATA: {
        "title_ru": "Корпоративные данные",
        "description_ru": "Публичные сведения организаций",
        "formats": ["company", "website", "filing"],
    },
    SourceCategory.DOCUMENTS: {
        "title_ru": "Документы",
        "description_ru": "PDF, DOCX, XLSX, CSV, XML, JSON",
        "formats": ["pdf", "docx", "xlsx", "csv", "xml", "json"],
    },
    SourceCategory.IMAGES: {
        "title_ru": "Изображения",
        "description_ru": "PNG, JPEG, TIFF, сканы",
        "formats": ["png", "jpeg", "tiff", "scan"],
    },
    SourceCategory.USER_UPLOADED_EVIDENCE: {
        "title_ru": "Загруженные доказательства",
        "description_ru": "Документы пользователя, архивы, экспорт",
        "formats": ["upload", "archive", "export"],
    },
}


def resolve_source_category(connector_category: ConnectorCategory | str) -> SourceCategory:
    if isinstance(connector_category, str):
        try:
            connector_category = ConnectorCategory(connector_category)
        except ValueError:
            return SourceCategory.PUBLIC_WEB
    return _CONNECTOR_TO_ICF.get(connector_category, SourceCategory.PUBLIC_WEB)


def source_category_registry() -> dict[str, Any]:
    categories = []
    for cat in SourceCategory:
        meta = dict(_ICF_CATALOG.get(cat, {}))
        meta["id"] = cat.value
        categories.append(meta)
    return {
        "rfc": "RFC-0014",
        "chapter": 2,
        "categories": categories,
        "connector_mapping": {k.value: v.value for k, v in _CONNECTOR_TO_ICF.items()},
    }
