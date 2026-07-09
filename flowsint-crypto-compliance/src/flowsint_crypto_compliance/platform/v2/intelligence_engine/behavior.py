"""RFC-0006 Behavior Engine — Ch.5 (привычки, не события)."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.intelligence_engine.types import IntelligenceEngineContext, PatternHit


def analyze_behavior_habits(ctx: IntelligenceEngineContext) -> tuple[list[PatternHit], dict[str, Any]]:
    """Analyze habits and flag deviations from baseline."""
    onchain = (ctx.screening or {}).get("onchain_summary") or {}
    hits: list[PatternHit] = []
    profile: dict[str, Any] = {
        "frequency": "unknown",
        "typical_hours": [],
        "typical_routes": [],
        "exchanges": [],
        "bridges": [],
        "networks": [ctx.chain] if ctx.chain else [],
    }

    inbound = int(onchain.get("inbound_count") or 0)
    outbound = int(onchain.get("outbound_count") or 0)
    total = inbound + outbound

    if total > 50:
        profile["frequency"] = "high"
    elif total > 10:
        profile["frequency"] = "medium"
    elif total > 0:
        profile["frequency"] = "low"

    intervals = onchain.get("intervals_hours") or onchain.get("tx_intervals") or []
    if isinstance(intervals, list) and intervals:
        avg = sum(float(x) for x in intervals if _num(x)) / max(len(intervals), 1)
        profile["typical_interval_hours"] = round(avg, 2)
        if avg < 1.0:
            hits.append(
                PatternHit(
                    code="RAPID_BURST",
                    title_ru="Аномалия: слишком частые операции",
                    description_ru=f"Средний интервал {avg:.2f} ч — отклонение от типичного поведения.",
                    confidence=0.78,
                    signals=["temporal", "frequency"],
                )
            )

    volume_change = onchain.get("volume_change_ratio")
    if volume_change is not None and _num(volume_change) and float(volume_change) > 2.5:
        hits.append(
            PatternHit(
                code="VOLUME_SPIKE",
                title_ru="Изменение объёмов",
                description_ru=f"Рост объёма в {float(volume_change):.1f}x от базовой линии.",
                confidence=0.74,
                signals=["volume"],
                explain={"ratio": float(volume_change)},
            )
        )

    bridges = onchain.get("bridge_hops") or onchain.get("bridges") or []
    if bridges:
        profile["bridges"] = bridges if isinstance(bridges, list) else [bridges]
        hits.append(
            PatternHit(
                code="BRIDGE_HABIT",
                title_ru="Маршруты через мосты",
                description_ru=f"Использовано мостов: {len(profile['bridges'])}.",
                confidence=0.7,
                signals=["bridge", "route"],
            )
        )

    exchanges = (ctx.attribution or {}).get("exchanges") or []
    if exchanges:
        profile["exchanges"] = exchanges

    stability = 0.85 if not hits else max(0.2, 0.85 - len(hits) * 0.15)
    return hits, {"profile": profile, "behavior_stability": round(stability, 2)}


def _num(v: Any) -> bool:
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False
