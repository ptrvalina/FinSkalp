"""RFC-15 Ch.9 — multi-dimensional confidence for operator explainability."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from flowsint_crypto_compliance.platform.v2.confidence_model import (
    calculate_confidence,
    independent_source_count,
    source_quality_score,
)


class ConfidenceDimensions(BaseModel):
    """Four explainable axes + integral risk score (0–100)."""

    identity_confidence: float = Field(..., ge=0.0, le=1.0, description="Entity identification certainty")
    evidence_strength: float = Field(..., ge=0.0, le=1.0, description="Independent evidence corroboration")
    relationship_confidence: float = Field(..., ge=0.0, le=1.0, description="Graph/link confidence")
    source_reliability: float = Field(..., ge=0.0, le=1.0, description="Empirical source trust")
    aggregate_risk_score: float = Field(..., ge=0.0, le=100.0, description="Integral risk index")
    explain_ru: dict[str, Any] = Field(default_factory=dict)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def build_confidence_dimensions(
    screening: dict[str, Any],
    *,
    attribution: dict[str, Any] | None = None,
) -> ConfidenceDimensions:
    """Derive RFC-15 dimensions from wallet screening / fusion payloads."""
    attribution = attribution or {}
    findings = screening.get("findings") or []
    evidence_chain = screening.get("evidence_chain") or []
    source_status = screening.get("source_status") or {}
    onchain = screening.get("onchain_summary") or {}
    risk_score = float(screening.get("risk_score") or 0.0)
    base_conf = float(screening.get("confidence") or 0.5)

    # Identity — label match + sanctions clarity
    label_conf = 0.45
    for f in findings:
        if f.get("category") or "реестр" in str(f.get("title_ru", "")).lower():
            label_conf = max(label_conf, float(f.get("confidence") or 0.65))
    if attribution.get("primary_label"):
        label_conf = max(label_conf, float(attribution["primary_label"].get("confidence") or 0.7))
    identity = _clamp01(label_conf)

    # Evidence strength — independent evidence families
    families = set()
    for ev in evidence_chain:
        families.add(str(ev).split(":")[0] if ":" in str(ev) else str(ev))
    n_indep = max(1, len(families))
    evidence_strength = _clamp01(0.35 + 0.12 * min(n_indep, 5) + 0.05 * min(len(findings), 6))

    # Relationship — exposure / counterparty graph signals
    kyt = onchain.get("kyt_exposure") or {}
    cp_count = int(kyt.get("connection_count") or onchain.get("counterparties") or 0)
    linkage = attribution.get("linkage_scores") or []
    rel_base = 0.4
    if cp_count:
        rel_base += min(0.35, cp_count * 0.03)
    if linkage:
        rel_base += min(0.25, sum(float(x) for x in linkage[:5]) / max(len(linkage), 1) * 0.25)
    relationship_confidence = _clamp01(rel_base)

    # Source reliability — live source health + quality heuristic
    ok_sources = sum(1 for v in source_status.values() if str(v).lower() in ("ok", "hit", "live"))
    total_sources = max(1, len(source_status))
    reliability_ratio = ok_sources / total_sources
    source_keys = [k for k in source_status if source_status.get(k) == "ok"]
    quality = (
        sum(source_quality_score(k) for k in source_keys) / len(source_keys)
        if source_keys
        else source_quality_score("unknown")
    )
    source_reliability = _clamp01(0.5 * reliability_ratio + 0.5 * quality)

    calc = calculate_confidence(
        sources=list(families) or ["unknown"],
        base_confidence=base_conf,
    )

    explain_ru = {
        "identity": (
            f"Уверенность в идентификации: {identity:.0%} — метки реестра и атрибуция сущности."
        ),
        "evidence": (
            f"Сила доказательств: {evidence_strength:.0%} — "
            f"{n_indep} независимых семейств, {len(findings)} находок."
        ),
        "relationship": (
            f"Достоверность связей: {relationship_confidence:.0%} — "
            f"контрагенты/экспозиция: {cp_count}."
        ),
        "source": (
            f"Надёжность источников: {source_reliability:.0%} — "
            f"{ok_sources}/{total_sources} источников в статусе ok."
        ),
        "composite_confidence": round(calc.composite, 3),
        "independent_sources": independent_source_count(list(families)),
        "formula_ru": (
            "Интегральный risk score не заменяет юридический вывод; "
            "раскрывается по четырём осям confidence."
        ),
    }

    return ConfidenceDimensions(
        identity_confidence=round(identity, 3),
        evidence_strength=round(evidence_strength, 3),
        relationship_confidence=round(relationship_confidence, 3),
        source_reliability=round(source_reliability, 3),
        aggregate_risk_score=round(risk_score, 1),
        explain_ru=explain_ru,
    )
