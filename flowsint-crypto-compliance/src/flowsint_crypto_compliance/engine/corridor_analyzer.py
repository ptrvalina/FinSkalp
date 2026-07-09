from __future__ import annotations

from dataclasses import dataclass

from flowsint_crypto_compliance.cis.coverage import CIS_CORRIDORS, DomesticEvidenceSource


@dataclass
class CorridorMatch:
    corridor: tuple[str, ...]
    matched_regions: list[str]
    coverage: float  # 0..1 how much of corridor is observed
    confidence: float
    evidence: list[str]


class CorridorAnalyzer:
    """
    Score observed regions against known CIS cross-border corridors.

    Example: anchors RU + KZ + TR on one trace → corridor (RU, KZ, TR, AE)
    even without any external risk label on intermediate wallets.
    """

    def match(self, observed_regions: list[str]) -> list[CorridorMatch]:
        observed = [r.upper() for r in observed_regions if r]
        if len(observed) < 2:
            return []

        unique_observed = list(dict.fromkeys(observed))
        results: list[CorridorMatch] = []

        for corridor in CIS_CORRIDORS:
            matched = [r for r in unique_observed if r in corridor]
            if len(matched) < 2:
                continue

            coverage = len(matched) / len(corridor)
            order_score = _order_consistency(matched, corridor)
            confidence = round(min(1.0, 0.5 * coverage + 0.5 * order_score), 3)

            evidence = [
                f"corridor:{'→'.join(corridor)}",
                f"observed:{'→'.join(matched)}",
                f"source:{DomesticEvidenceSource.CROSS_BORDER_CORRIDOR.value}",
            ]
            results.append(
                CorridorMatch(
                    corridor=corridor,
                    matched_regions=matched,
                    coverage=round(coverage, 3),
                    confidence=confidence,
                    evidence=evidence,
                )
            )

        return sorted(results, key=lambda m: m.confidence, reverse=True)

    def best_corridor(self, observed_regions: list[str]) -> CorridorMatch | None:
        matches = self.match(observed_regions)
        return matches[0] if matches else None


def _order_consistency(matched: list[str], corridor: tuple[str, ...]) -> float:
    """Higher score when matched regions follow corridor order."""
    indices = [corridor.index(r) for r in matched if r in corridor]
    if len(indices) < 2:
        return 0.5
    increasing = sum(1 for i in range(len(indices) - 1) if indices[i] < indices[i + 1])
    return increasing / (len(indices) - 1)
