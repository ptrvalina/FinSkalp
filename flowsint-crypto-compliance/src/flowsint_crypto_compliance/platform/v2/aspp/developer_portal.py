"""RFC-0019 Ch.15 — developer portal manifest."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.aspp.types import SDKLanguage
from flowsint_crypto_compliance.platform.v2.aspp.versioning import PLATFORM_API_VERSION


def developer_portal_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0019",
        "chapter": 15,
        "schema_version": PLATFORM_API_VERSION,
        "title_ru": "Портал разработчика FinSkalp",
        "docs": {
            "rfc_index": "/docs/rfc/README.md",
            "aspp_rfc": "/docs/rfc/RFC-0019-api-sdk-plugin-platform.md",
            "completion": "/docs/architecture/v2/rfc0019-completion.md",
            "api_catalog": "/api/platform/v2/aspp/rest-catalog",
            "event_catalog": "/api/platform/v2/aspp/events",
            "plugin_guide": "/docs/architecture/v2/README.md",
        },
        "sandbox": {
            "enabled": True,
            "base_url": "/api/platform/v2",
            "demo_token_header": "X-Demo-Token",
            "rate_limit_rpm": 120,
            "tenant_id": "00000000-0000-0000-0000-000000000001",
        },
        "sdks": [lang.value for lang in SDKLanguage],
        "changelog": [
            {
                "version": "2.0.0",
                "date": "2026-07-09",
                "summary_ru": "RFC-0019 ASPP v2.0 — API First, Plugin First, SDK 4 языка",
            },
            {
                "version": "1.0.0",
                "date": "2026-03-01",
                "summary_ru": "RFC-0002 Platform v2 foundation",
            },
        ],
        "quickstart_ru": [
            "Получить JWT или API key",
            "Изучить REST каталог /aspp/rest-catalog",
            "Зарегистрировать плагин POST /aspp/plugins/register",
            "Подписаться на webhook POST /aspp/webhooks/subscribe",
        ],
        "support": {
            "issues": "https://github.com/flowsint/flowsint/issues",
            "email": "dev@flowsint.io",
        },
    }
