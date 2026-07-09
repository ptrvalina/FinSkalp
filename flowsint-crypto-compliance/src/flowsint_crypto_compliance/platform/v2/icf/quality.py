"""RFC-0014 Ch.7, 17 — quality engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.platform.v2.connectors.types import SourceQualityProfile


@dataclass
class QualityScore:
    completeness: float = 0.0
    freshness: float = 0.0
    origin: float = 0.0
    stability: float = 0.0
    error_rate: float = 0.0
    structure: float = 0.0
    repeatability: float = 0.0
    composite: float = 0.0
    explain: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "completeness": self.completeness,
            "freshness": self.freshness,
            "origin": self.origin,
            "stability": self.stability,
            "error_rate": self.error_rate,
            "structure": self.structure,
            "repeatability": self.repeatability,
            "composite": self.composite,
            "explain": self.explain,
        }


class QualityEngine:
    """Score source quality — feeds confidence calculation."""

    def score(
        self,
        *,
        profile: SourceQualityProfile,
        records: list[dict[str, Any]],
        validation_errors: list[str],
        last_collected_at: datetime | None = None,
    ) -> QualityScore:
        total = max(len(records), 1)
        filled = sum(1 for r in records if r.get("entity_value") and r.get("entity_type"))
        completeness = min(1.0, filled / total) * profile.completeness

        now = datetime.now(timezone.utc)
        if last_collected_at:
            age_hours = max(0.0, (now - last_collected_at).total_seconds() / 3600)
            freshness = max(0.0, 1.0 - age_hours / 168.0)
        else:
            freshness = 0.8

        origin = profile.trust_level if profile.official else profile.trust_level * 0.85
        stability = profile.stability
        error_rate = min(1.0, len(validation_errors) / max(total, 1))
        structure = sum(
            1 for r in records if isinstance(r.get("payload"), dict) or r.get("entity_type")
        ) / total
        repeatability = profile.availability * (1.0 - profile.error_rate)

        composite = (
            completeness * 0.2
            + freshness * 0.15
            + origin * 0.2
            + stability * 0.15
            + (1.0 - error_rate) * 0.1
            + structure * 0.1
            + repeatability * 0.1
        )

        return QualityScore(
            completeness=round(completeness, 4),
            freshness=round(freshness, 4),
            origin=round(origin, 4),
            stability=round(stability, 4),
            error_rate=round(error_rate, 4),
            structure=round(structure, 4),
            repeatability=round(repeatability, 4),
            composite=round(composite, 4),
            explain={
                "record_count": len(records),
                "validation_errors": len(validation_errors),
                "profile_provenance": profile.provenance,
            },
        )


_engine: QualityEngine | None = None


def get_quality_engine() -> QualityEngine:
    global _engine
    if _engine is None:
        _engine = QualityEngine()
    return _engine
