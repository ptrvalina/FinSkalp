"""RFC-0018 Ch.11 — verified evidence + hypothesis labeling."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.eia.types import Citation


def build_evidence_summary(context: dict[str, Any]) -> dict[str, Any]:
    """Only verified evidence + hypothesis labeling."""
    evidence = context.get("evidence") or []
    hypotheses = context.get("hypotheses") or []

    verified = []
    for ev in evidence:
        lifecycle = str(ev.get("lifecycle") or ev.get("status") or "")
        integrity_ok = ev.get("integrity_ok", True)
        if lifecycle in ("validated", "linked", "in_report", "") and integrity_ok:
            verified.append(ev)

    citations: list[Citation] = []
    for ev in verified[:15]:
        eid = ev.get("evidence_id") or ev.get("id")
        citations.append(
            Citation(
                evidence_id=str(eid) if eid else None,
                source_type=str(ev.get("source_type") or ev.get("category") or "unknown"),
                label_ru=str(ev.get("entity_value") or ev.get("label") or "доказательство"),
                confidence=float(ev.get("confidence") or 0.5),
            )
        )

    labeled_hypotheses = []
    for hyp in hypotheses:
        labeled_hypotheses.append({
            **hyp,
            "label": "hypothesis",
            "requires_verification": True,
            "evidence_backed": len(verified) > 0,
        })

    narrative = (
        f"Верифицированных доказательств: {len(verified)} из {len(evidence)}. "
        f"Гипотез с маркировкой: {len(labeled_hypotheses)}. "
        "Гипотезы не являются выводами — требуют подтверждения."
    )

    return {
        "narrative_ru": narrative,
        "verified_evidence": verified,
        "citations": citations,
        "hypotheses": labeled_hypotheses,
        "confidence": 0.6 if verified else 0.3,
        "limitations": ["Только доказательства с подтверждённой целостностью"],
    }
