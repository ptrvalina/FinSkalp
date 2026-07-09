"""RFC-0006 Hypothesis Engine — Ch.6."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.intelligence_engine.types import (
    Hypothesis,
    IntelligenceEngineContext,
    PatternHit,
)


def generate_hypotheses(
    ctx: IntelligenceEngineContext,
    patterns: list[PatternHit],
    prior_findings: list[dict[str, Any]] | None = None,
) -> list[Hypothesis]:
    """Build probabilistic hypotheses — not conclusions."""
    hyps: list[Hypothesis] = []
    prior = prior_findings or ctx.prior_findings or []

    if any(p.code == "SHARED_IP" for p in patterns):
        hyps.append(
            Hypothesis(
                code="SAME_OWNER_WALLET",
                statement_ru="Возможно, данные кошельки принадлежат одному владельцу (общий IP).",
                confidence=0.62,
                explain={"basis": "SHARED_IP", "rule_ru": "Совпадение IP в OSINT"},
            )
        )

    if any(p.code == "REPEATED_LEGAL_ENTITY" for p in patterns):
        hyps.append(
            Hypothesis(
                code="ORG_CONTROLS_ADDRESSES",
                statement_ru="Возможно, организация контролирует группу адресов.",
                confidence=0.68,
                explain={"basis": "REPEATED_LEGAL_ENTITY"},
            )
        )

    if any(p.code in ("PASS_THROUGH_ROUTE", "BRIDGE_HABIT") for p in patterns):
        hyps.append(
            Hypothesis(
                code="SINGLE_GROUP_CHAIN",
                statement_ru="Возможно, цепочка переводов используется одной группой.",
                confidence=0.65,
                explain={"basis": "route_pattern"},
            )
        )

    if any(f.get("code") == "CROSS_ENGINE_CORRELATION" for f in prior):
        hyps.append(
            Hypothesis(
                code="CROSS_INVESTIGATION_LINK",
                statement_ru="Возможно, найдена связь с другим контекстом расследования.",
                confidence=0.55,
                explain={"basis": "correlation"},
            )
        )

    labels = (ctx.attribution or {}).get("labels") or {}
    if len(labels) >= 2:
        hyps.append(
            Hypothesis(
                code="SHARED_ATTRIBUTION_CLUSTER",
                statement_ru="Возможно, несколько адресов объединены одним кластером атрибуции.",
                confidence=0.6,
                explain={"label_count": len(labels)},
            )
        )

    if ctx.address and ctx.case_ref:
        hyps.append(
            Hypothesis(
                code="CASE_ANCHOR_WALLET",
                statement_ru=f"Возможно, адрес {ctx.address[:12]}… — ключевой узел дела {ctx.case_ref}.",
                confidence=0.5,
                explain={"address": ctx.address, "case_ref": ctx.case_ref},
            )
        )

    return hyps
