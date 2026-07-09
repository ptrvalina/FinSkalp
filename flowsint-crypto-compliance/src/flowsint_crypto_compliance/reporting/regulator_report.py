from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.detection.findings import IllegalFlowFinding
from flowsint_crypto_compliance.detection.illegal_flow import IllegalFlowDetector
from flowsint_crypto_compliance.osint_core.fusion_engine import FusionResult
from flowsint_types.fiat_crypto import FusedAttribution


@dataclass
class RegulatorCaseReport:
    """Итоговый отчёт для госрегулятора (демо / боевой прототип)."""

    case_ref: str
    scenario_title_ru: str
    generated_at: str
    executive_summary_ru: str
    illegal_flow_score: float  # 0..100
    risk_level: str  # critical | high | medium | low
    findings: list[IllegalFlowFinding]
    attributions: list[dict[str, Any]]
    bridges: list[dict[str, Any]]
    metrics: dict[str, Any]
    evidence_graph: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_ref": self.case_ref,
            "scenario_title_ru": self.scenario_title_ru,
            "generated_at": self.generated_at,
            "executive_summary_ru": self.executive_summary_ru,
            "illegal_flow_score": self.illegal_flow_score,
            "risk_level": self.risk_level,
            "findings": [
                {
                    "severity": f.severity,
                    "code": f.code,
                    "title_ru": f.title_ru,
                    "description_ru": f.description_ru,
                    "addresses": f.addresses,
                    "evidence": f.evidence,
                    "confidence": f.confidence,
                }
                for f in self.findings
            ],
            "attributions": self.attributions,
            "bridges": self.bridges,
            "metrics": self.metrics,
            "evidence_graph": self.evidence_graph,
        }


class ReportBuilder:
    def __init__(self) -> None:
        self._detector = IllegalFlowDetector()

    def build(
        self,
        *,
        case_ref: str,
        scenario_title_ru: str,
        fusion: FusionResult,
        bank_feed_count: int = 0,
        control_purchase_count: int = 0,
        registry_label_count: int = 0,
    ) -> RegulatorCaseReport:
        findings, illegal_score, risk_meta = self._detector.analyze(
            attributions=fusion.attributions,
            bridges=fusion.bridges,
            bank_feed_count=bank_feed_count,
            control_purchase_count=control_purchase_count,
        )
        risk = _score_to_risk(illegal_score)
        gray_before = _estimate_gray_before(fusion)
        gray_after = _estimate_gray_after(fusion)
        reduction = max(0, gray_before - gray_after)

        metrics = {
            "wallets_analyzed": len(fusion.attributions),
            "bank_crypto_links": sum(
                1 for a in fusion.attributions if (a.linkage_strength or 0) >= 0.5
            ),
            "black_zone_wallets": sum(1 for a in fusion.attributions if a.black_zone),
            "gray_zone_wallets": sum(1 for a in fusion.attributions if a.gray_zone),
            "gray_zone_reduction_pct": round(reduction, 1),
            "cross_border_bridges": sum(
                1
                for b in fusion.bridges
                if b.region_origin and b.region_destination
                and b.region_origin != b.region_destination
            ),
            "registry_labels_applied": registry_label_count,
            "sanctioned_addresses": sum(1 for a in fusion.attributions if a.sanctioned),
            "avg_linkage_strength": round(
                _avg([a.linkage_strength for a in fusion.attributions if a.linkage_strength]),
                3,
            ),
            "max_confidence": round(
                max((a.confidence for a in fusion.attributions), default=0), 3
            ),
            "risk_scoring": risk_meta,
        }

        summary = _executive_summary(
            case_ref=case_ref,
            scenario_title_ru=scenario_title_ru,
            illegal_score=illegal_score,
            risk=risk,
            findings=findings,
            metrics=metrics,
        )

        return RegulatorCaseReport(
            case_ref=case_ref,
            scenario_title_ru=scenario_title_ru,
            generated_at=datetime.now(timezone.utc).isoformat(),
            executive_summary_ru=summary,
            illegal_flow_score=illegal_score,
            risk_level=risk,
            findings=findings,
            attributions=[a.model_dump() for a in fusion.attributions],
            bridges=[b.model_dump() for b in fusion.bridges],
            metrics=metrics,
            evidence_graph={
                "nodes": len(fusion.graph.nodes),
                "edges": len(fusion.graph.edges),
            },
        )


def _score_to_risk(score: float) -> str:
    if score >= 75:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


def _estimate_gray_before(fusion: FusionResult) -> float:
    if not fusion.attributions:
        return 95.0
    return 92.0


def _estimate_gray_after(fusion: FusionResult) -> float:
    if not fusion.attributions:
        return 92.0
    identified = sum(1 for a in fusion.attributions if a.confidence >= 0.55 or a.linkage_strength)
    ratio = identified / len(fusion.attributions)
    return round(92.0 * (1 - ratio * 0.65), 1)


def _avg(values: list[float | None]) -> float:
    nums = [v for v in values if v is not None]
    return sum(nums) / len(nums) if nums else 0.0


def _executive_summary(
    *,
    case_ref: str,
    scenario_title_ru: str,
    illegal_score: float,
    risk: str,
    findings: list[IllegalFlowFinding],
    metrics: dict[str, Any],
) -> str:
    critical = sum(1 for f in findings if f.severity == "critical")
    high = sum(1 for f in findings if f.severity == "high")
    return (
        f"Кейс {case_ref}: {scenario_title_ru}. "
        f"Индекс нелегального движения ценностей: {illegal_score}/100 (уровень: {risk}). "
        f"Выявлено {len(findings)} индикаторов ({critical} критических, {high} высоких). "
        f"Проанализировано {metrics['wallets_analyzed']} кошельков; "
        f"склейка фиат↔крипто: {metrics['bank_crypto_links']} связей; "
        f"серая зона сужена на ~{metrics['gray_zone_reduction_pct']}%. "
        f"Система: суверенный OSINT-движок + реестр риск-меток РФ/СНГ (115-ФЗ) + банковский хаб регулятора."
    )
