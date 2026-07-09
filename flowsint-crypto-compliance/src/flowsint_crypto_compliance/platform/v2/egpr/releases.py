"""RFC-0022 Ch.6 — release management and semver manifest."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flowsint_crypto_compliance.platform.v2.idoo.versioning import versioning_manifest


def _changelog_path() -> str:
    root = Path(__file__).resolve().parents[6]
    changelog = root / "CHANGELOG.md"
    return "CHANGELOG.md" if changelog.is_file() else ""


def releases_manifest() -> dict[str, Any]:
    versions = versioning_manifest()
    return {
        "rfc": "RFC-0022",
        "chapter": 6,
        "semver_policy": "semver",
        "platform_version": versions.get("platform_version", "unknown"),
        "components": versions.get("components", {}),
        "changelog_path": _changelog_path(),
        "release_channels": ["stable", "lts", "preview"],
        "current_channel": "stable",
        "release_notes_stub": {
            "version": versions.get("platform_version", "2.0.0"),
            "date": "2026-07-09",
            "highlights_ru": [
                "Volume I Enterprise Architecture Book завершён (RFC-0000 — RFC-0022)",
                "22 RFC реализованы на уровне platform/v2/",
                "Единый BFF gateway и compliance UI",
            ],
            "breaking_changes": [],
            "migration_notes": "См. CHANGELOG.md и completion docs",
        },
        "principle_ru": "Семантическое версионирование и прозрачные release notes",
    }
