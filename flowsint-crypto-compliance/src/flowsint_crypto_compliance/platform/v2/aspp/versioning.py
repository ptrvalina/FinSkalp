"""RFC-0019 Ch.12 — platform API semver."""

from __future__ import annotations

from typing import Any

PLATFORM_API_VERSION = "2.0.0"
PLATFORM_API_MAJOR = 2
PLATFORM_API_MINOR = 0
PLATFORM_API_PATCH = 0


def platform_version_manifest() -> dict[str, Any]:
    return {
        "version": PLATFORM_API_VERSION,
        "major": PLATFORM_API_MAJOR,
        "minor": PLATFORM_API_MINOR,
        "patch": PLATFORM_API_PATCH,
        "semver": PLATFORM_API_VERSION,
        "api_prefix": "/api/platform/v2",
        "deprecation_policy_ru": "Минорные версии обратно совместимы; major — с миграционным окном 90 дней",
        "supported_versions": ["2.0.0"],
        "beta_versions": ["2.1.0-beta"],
    }
