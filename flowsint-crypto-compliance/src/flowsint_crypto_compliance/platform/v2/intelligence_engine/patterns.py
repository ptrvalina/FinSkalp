"""RFC-0006 Pattern Engine — Ch.4."""

from __future__ import annotations

from collections import Counter
from typing import Any

from flowsint_crypto_compliance.platform.v2.intelligence_engine.types import IntelligenceEngineContext, PatternHit


def detect_patterns(ctx: IntelligenceEngineContext) -> list[PatternHit]:
    hits: list[PatternHit] = []
    onchain = (ctx.screening or {}).get("onchain_summary") or {}
    mentions = ctx.mentions or []
    attribution = ctx.attribution or {}

    amounts = _collect_values(mentions, ("amount", "value", "sum"))
    if amounts:
        counter = Counter(round(float(a), 2) for a in amounts if _is_num(a))
        for val, cnt in counter.items():
            if cnt >= 2:
                hits.append(
                    PatternHit(
                        code="REPEATED_AMOUNT",
                        title_ru="Повторяющиеся суммы",
                        description_ru=f"Сумма {val} встречается {cnt} раз.",
                        confidence=min(0.95, 0.5 + cnt * 0.1),
                        signals=["amount"],
                        explain={"amount": val, "count": cnt},
                    )
                )

    domains = _collect_values(mentions, ("domain", "entity_value", "url"))
    domain_counter = Counter(d for d in domains if d and "." in str(d))
    for dom, cnt in domain_counter.items():
        if cnt >= 2:
            hits.append(
                PatternHit(
                    code="REPEATED_DOMAIN",
                    title_ru="Повторяющиеся домены",
                    description_ru=f"Домен {dom} — {cnt} совпадений.",
                    confidence=min(0.9, 0.45 + cnt * 0.12),
                    signals=["domain"],
                    explain={"domain": dom, "count": cnt},
                )
            )

    ips = _collect_values(mentions, ("ip", "ip_address"))
    ip_counter = Counter(ips)
    for ip, cnt in ip_counter.items():
        if cnt >= 2:
            hits.append(
                PatternHit(
                    code="SHARED_IP",
                    title_ru="Совпадающие IP",
                    description_ru=f"IP {ip} встречается {cnt} раз.",
                    confidence=0.75,
                    signals=["ip"],
                    explain={"ip": ip, "count": cnt},
                )
            )

    telegrams = _collect_values(mentions, ("telegram", "username"))
    for tg, cnt in Counter(telegrams).items():
        if cnt >= 2:
            hits.append(
                PatternHit(
                    code="REPEATED_TELEGRAM",
                    title_ru="Одинаковые Telegram",
                    description_ru=f"@{tg} — {cnt} упоминаний.",
                    confidence=0.8,
                    signals=["telegram"],
                )
            )

    inbound = int(onchain.get("inbound_count") or 0)
    outbound = int(onchain.get("outbound_count") or 0)
    if inbound > 3 and outbound > 3 and abs(inbound - outbound) <= 2:
        hits.append(
            PatternHit(
                code="PASS_THROUGH_ROUTE",
                title_ru="Одинаковые маршруты переводов",
                description_ru=f"Pass-through: in={inbound}, out={outbound}.",
                confidence=0.7,
                signals=["route", "volume"],
                explain={"inbound": inbound, "outbound": outbound},
            )
        )

    labels = attribution.get("labels") or {}
    orgs = [str(v.get("label")) for v in labels.values() if isinstance(v, dict) and v.get("category") == "exchange"]
    if len(set(orgs)) == 1 and len(orgs) >= 2:
        hits.append(
            PatternHit(
                code="REPEATED_LEGAL_ENTITY",
                title_ru="Повторяющиеся юридические лица / сервисы",
                description_ru=f"Общий сервис: {orgs[0]}.",
                confidence=0.72,
                signals=["entity", "exchange"],
            )
        )

    contracts = onchain.get("contracts") or onchain.get("smart_contracts") or []
    if isinstance(contracts, list) and len(contracts) >= 2:
        hits.append(
            PatternHit(
                code="SHARED_SMART_CONTRACT",
                title_ru="Общие Smart Contracts",
                description_ru=f"Контрактов в контексте: {len(contracts)}.",
                confidence=0.68,
                signals=["smart_contract"],
            )
        )

    return hits


def _collect_values(mentions: list[dict[str, Any]], keys: tuple[str, ...]) -> list[str]:
    out: list[str] = []
    for m in mentions:
        if not isinstance(m, dict):
            continue
        for k in keys:
            v = m.get(k)
            if v:
                out.append(str(v).lower().strip())
                break
    return out


def _is_num(v: Any) -> bool:
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False
