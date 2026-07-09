"""
Bayesian fusion of independent OSINT evidence.

Multiplies error probabilities (1 − p) across independent dependency groups;
sources in the same dependency_group are not double-counted (best signal per group).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from flowsint_crypto_compliance.osint.source_reliability import (
    apply_source_reliability,
    default_reliability_for_source,
)


@dataclass
class EvidenceFinding:
    source_type: str
    raw_confidence: float
    source_name: str = ""
    dependency_group: str | None = None
    finding_id: str | None = None
    title_ru: str = ""
    url: str | None = None

    def effective_group_key(self) -> str:
        if self.dependency_group:
            return self.dependency_group
        name = (self.source_name or self.source_type or "unknown").strip().lower()
        return f"{self.source_type}:{name}"


@dataclass
class SourceContribution:
    source_type: str
    source_name: str
    dependency_group: str
    raw_confidence: float
    source_reliability: float
    adjusted_confidence: float
    error_probability: float
    included_in_fusion: bool
    reason_ru: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_name": self.source_name,
            "dependency_group": self.dependency_group,
            "raw_confidence": round(self.raw_confidence, 4),
            "source_reliability": round(self.source_reliability, 4),
            "adjusted_confidence": round(self.adjusted_confidence, 4),
            "error_probability": round(self.error_probability, 4),
            "included_in_fusion": self.included_in_fusion,
            "reason_ru": self.reason_ru,
        }


@dataclass
class FusionConfidenceResult:
    composite_confidence: float
    independent_groups: int
    explain: list[SourceContribution] = field(default_factory=list)
    method: str = "bayesian_independent_groups"

    def to_dict(self) -> dict[str, Any]:
        return {
            "composite_confidence": round(self.composite_confidence, 4),
            "composite_pct": round(self.composite_confidence * 100, 1),
            "independent_groups": self.independent_groups,
            "method": self.method,
            "explain": [c.to_dict() for c in self.explain],
        }


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def fuse_evidence(
    findings: list[EvidenceFinding],
    *,
    reliability_map: dict[str, float] | None = None,
) -> FusionConfidenceResult:
    """Fuse findings via Bayesian combination of independent dependency groups."""
    if not findings:
        return FusionConfidenceResult(composite_confidence=0.0, independent_groups=0)

    explain: list[SourceContribution] = []
    best_by_group: dict[str, tuple[float, EvidenceFinding, float, float]] = {}

    for f in findings:
        raw = _clamp01(f.raw_confidence)
        rel = apply_source_reliability(
            f.source_name or f.source_type,
            default_reliability_for_source(f.source_type, reliability_map),
            reliability_map=reliability_map,
        )
        adjusted = _clamp01(raw * rel)
        group = f.effective_group_key()
        err = 1.0 - adjusted

        prev = best_by_group.get(group)
        if prev is None or adjusted > prev[0]:
            best_by_group[group] = (adjusted, f, rel, err)

    product_err = 1.0
    for group, (adjusted, f, rel, err) in best_by_group.items():
        product_err *= err
        explain.append(
            SourceContribution(
                source_type=f.source_type,
                source_name=f.source_name or f.source_type,
                dependency_group=group,
                raw_confidence=f.raw_confidence,
                source_reliability=rel,
                adjusted_confidence=adjusted,
                error_probability=err,
                included_in_fusion=True,
                reason_ru="Лучший сигнал в группе зависимостей",
            )
        )

    for f in findings:
        group = f.effective_group_key()
        winner = best_by_group.get(group)
        if winner and winner[1] is not f:
            raw = _clamp01(f.raw_confidence)
            rel = apply_source_reliability(
                f.source_name or f.source_type,
                default_reliability_for_source(f.source_type, reliability_map),
                reliability_map=reliability_map,
            )
            explain.append(
                SourceContribution(
                    source_type=f.source_type,
                    source_name=f.source_name or f.source_type,
                    dependency_group=group,
                    raw_confidence=raw,
                    source_reliability=rel,
                    adjusted_confidence=_clamp01(raw * rel),
                    error_probability=1.0 - _clamp01(raw * rel),
                    included_in_fusion=False,
                    reason_ru="Поглощено более сильным сигналом той же группы",
                )
            )

    composite = _clamp01(1.0 - product_err)
    explain.sort(key=lambda c: (-c.adjusted_confidence, c.source_type))
    return FusionConfidenceResult(
        composite_confidence=composite,
        independent_groups=len(best_by_group),
        explain=explain,
    )


def fuse_mention_hits(hits: list[Any], *, reliability_map: dict[str, float] | None = None) -> FusionConfidenceResult:
    """Adapter for OpenMentionHit or dict mentions from Scalpel."""
    findings: list[EvidenceFinding] = []
    for i, h in enumerate(hits):
        if hasattr(h, "source_type"):
            dep = getattr(h, "dependency_group", None)
            if dep is None:
                dep = f"{h.source_type}:{(h.source_name or '').lower()}"
            findings.append(
                EvidenceFinding(
                    source_type=h.source_type,
                    source_name=h.source_name or h.source_type,
                    raw_confidence=float(h.confidence or 0.5),
                    dependency_group=dep,
                    finding_id=f"m{i}",
                    title_ru=getattr(h, "title_ru", "") or "",
                    url=getattr(h, "url", None),
                )
            )
        elif isinstance(h, dict):
            st = str(h.get("source_type") or "unknown")
            sn = str(h.get("source_name") or st)
            findings.append(
                EvidenceFinding(
                    source_type=st,
                    source_name=sn,
                    raw_confidence=float(h.get("confidence") or 0.5),
                    dependency_group=h.get("dependency_group") or f"{st}:{sn.lower()}",
                    finding_id=str(h.get("id") or f"m{i}"),
                    title_ru=str(h.get("title_ru") or ""),
                    url=h.get("url"),
                )
            )
    return fuse_evidence(findings, reliability_map=reliability_map)


def correlation_score_from_fusion(fusion: FusionConfidenceResult) -> float:
    """Legacy correlation_score compatible with open_osint pipeline."""
    if fusion.independent_groups <= 0:
        return 0.0
    base = min(1.0, fusion.independent_groups / 4.0)
    if fusion.composite_confidence >= 0.55:
        base = min(1.0, base + 0.1)
    if fusion.composite_confidence >= 0.75:
        base = min(1.0, base + 0.08)
    return round(base, 3)
