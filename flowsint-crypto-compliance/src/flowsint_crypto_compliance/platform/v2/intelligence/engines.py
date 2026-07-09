"""Specialized intelligence engines — RFC-0004 Ch.2–10."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.confidence_model import calculate_confidence
from flowsint_crypto_compliance.platform.v2.intelligence.base import IntelligenceEngine
from flowsint_crypto_compliance.platform.v2.intelligence.types import (
    EngineAnalysisResult,
    EngineKind,
    IntelligenceContext,
    IntelligenceFinding,
)

from flowsint_crypto_compliance.platform.v2.intelligence.analysis_helpers import (
    cluster_hints,
    corridor_hints,
    detect_bridge_signals,
    detect_mixer_signals,
    illegal_flow_risk_boost,
    temporal_correlation_signals,
)
from flowsint_crypto_compliance.platform.v2.intelligence.blockchain_capabilities import (
    blockchain_capabilities_manifest,
    get_chain_adapter_by_key,
    normalize_chain_key,
)

SUPPORTED_CHAINS = ("btc", "eth", "tron", "ltc", "bsc", "bnb", "polygon", "sol")


class BlockchainIntelligenceEngine(IntelligenceEngine):
    kind = EngineKind.BLOCKCHAIN
    title_ru = "Blockchain Intelligence Engine"
    maturity = "production"

    def analyze(self, ctx: IntelligenceContext) -> EngineAnalysisResult:
        findings: list[IntelligenceFinding] = []
        onchain = (ctx.screening or {}).get("onchain_summary") or {}
        chain = normalize_chain_key(ctx.chain)
        adapter_meta = get_chain_adapter_by_key(chain, use_memory=True)

        if adapter_meta:
            findings.append(
                IntelligenceFinding(
                    engine=self.kind,
                    code="CHAIN_ADAPTER",
                    title_ru=f"Адаптер {chain.upper()}",
                    description_ru="Единый интерфейс ChainAdapter подключён.",
                    confidence=0.95,
                    severity="info",
                    entity_type="blockchain_address",
                    entity_value=ctx.address,
                    explain={"chain": chain, "adapter": type(adapter_meta).__name__},
                )
            )

        inbound = int(onchain.get("inbound_count") or 0)
        outbound = int(onchain.get("outbound_count") or 0)
        if inbound + outbound > 0:
            findings.append(
                IntelligenceFinding(
                    engine=self.kind,
                    code="TX_ACTIVITY",
                    title_ru="Импорт транзакций",
                    description_ru=f"Входящих: {inbound}, исходящих: {outbound}.",
                    confidence=0.9,
                    severity="info",
                    entity_type="blockchain_address",
                    entity_value=ctx.address,
                    explain={"inbound": inbound, "outbound": outbound, "chain": chain},
                )
            )

        token_count = int(onchain.get("token_tx_count") or onchain.get("token_count") or 0)
        if token_count > 0:
            findings.append(
                IntelligenceFinding(
                    engine=self.kind,
                    code="TOKEN_IMPORT",
                    title_ru="Импорт токенов",
                    description_ru=f"Токен-транзакций: {token_count}.",
                    confidence=0.85,
                    severity="info",
                    entity_type="blockchain_address",
                    entity_value=ctx.address,
                )
            )

        for hit in detect_mixer_signals(ctx.attribution, ctx.screening):
            findings.append(
                IntelligenceFinding(
                    engine=self.kind,
                    code="MIXER_DETECTED",
                    title_ru="Выявление миксера/санкций",
                    description_ru=str(hit.get("label") or hit.get("code") or "mixer"),
                    confidence=float(hit.get("confidence") or 0.8),
                    severity="high",
                    entity_type="blockchain_address",
                    entity_value=str(hit.get("address") or ctx.address),
                    explain=hit,
                )
            )

        for hit in detect_bridge_signals(ctx.screening, ctx.attribution):
            findings.append(
                IntelligenceFinding(
                    engine=self.kind,
                    code="BRIDGE_LINK",
                    title_ru="Анализ мостов",
                    description_ru="Межсетевой или bridge-контрагент.",
                    confidence=float(hit.get("confidence") or 0.7),
                    severity="medium",
                    entity_type="blockchain_address",
                    entity_value=ctx.address,
                    explain=hit,
                )
            )

        for cluster in cluster_hints(ctx.screening, ctx.attribution):
            findings.append(
                IntelligenceFinding(
                    engine=self.kind,
                    code="CLUSTER_MATCH",
                    title_ru="Поиск кластеров",
                    description_ru=f"Кластер: {cluster.get('cluster_id', '—')}.",
                    confidence=float(cluster.get("confidence") or 0.65),
                    severity="medium",
                    entity_type="blockchain_address",
                    entity_value=ctx.address,
                    explain=cluster,
                )
            )

        exposure = (ctx.attribution or {}).get("exposure") or {}
        if exposure.get("connection_count", 0) > 0:
            findings.append(
                IntelligenceFinding(
                    engine=self.kind,
                    code="FLOW_CALCULATION",
                    title_ru="Расчёт финансовых потоков",
                    description_ru=f"Связей: {exposure.get('connection_count')}, in/out: {exposure.get('total_inbound')}/{exposure.get('total_outbound')}.",
                    confidence=0.75,
                    severity="info",
                    entity_type="blockchain_address",
                    entity_value=ctx.address,
                    explain=exposure,
                )
            )

        contracts = onchain.get("contracts") or onchain.get("smart_contracts") or []
        if contracts:
            findings.append(
                IntelligenceFinding(
                    engine=self.kind,
                    code="SMART_CONTRACT",
                    title_ru="Анализ смарт-контрактов",
                    description_ru=f"Контрактов: {len(contracts) if isinstance(contracts, list) else 1}.",
                    confidence=0.8,
                    severity="info",
                    explain={"contracts": contracts[:5] if isinstance(contracts, list) else contracts},
                )
            )

        conf = calculate_confidence(sources=["blockchain_explorer"], base_confidence=0.85)
        return EngineAnalysisResult(
            engine=self.kind,
            findings=findings,
            confidence=conf,
            explain=blockchain_capabilities_manifest(),
        )


class OsintIntelligenceEngine(IntelligenceEngine):
    kind = EngineKind.OSINT
    title_ru = "OSINT Intelligence Engine"
    maturity = "production"

    OSINT_CATEGORIES = (
        "social", "forum", "telegram", "news", "registry", "court_decision",
        "corporate", "document", "search", "archive", "scientific",
    )

    def analyze(self, ctx: IntelligenceContext) -> EngineAnalysisResult:
        findings: list[IntelligenceFinding] = []
        by_cat: dict[str, int] = {}

        for m in ctx.mentions:
            if not isinstance(m, dict):
                continue
            st = str(m.get("source_type") or m.get("collector_id") or "osint").lower()
            cat = _osint_category(st, m)
            by_cat[cat] = by_cat.get(cat, 0) + 1
            ev = str(m.get("entity_value") or m.get("mention") or m.get("url") or "")
            if not ev:
                continue
            findings.append(
                IntelligenceFinding(
                    engine=self.kind,
                    code="OSINT_MENTION",
                    title_ru="OSINT-упоминание",
                    description_ru=f"Категория: {cat}; объект: {ev[:80]}.",
                    confidence=float(m.get("confidence") or m.get("fusion_confidence") or 0.5),
                    severity="info",
                    entity_type=str(m.get("entity_type") or "domain"),
                    entity_value=ev,
                    explain={"category": cat, "source_type": st},
                )
            )

        conf = calculate_confidence(
            sources=["osint"] * max(1, len(ctx.mentions)),
            base_confidence=0.55,
        )
        return EngineAnalysisResult(
            engine=self.kind,
            findings=findings,
            confidence=conf,
            explain={"categories_seen": by_cat, "supported_categories": list(self.OSINT_CATEGORIES)},
        )


def _osint_category(source_type: str, mention: dict[str, Any]) -> str:
    mapping = {
        "telegram": "telegram",
        "forum": "forum",
        "social": "social",
        "news": "news",
        "registry": "registry",
        "court": "court_decision",
        "scalpel": "search",
        "domain": "corporate",
    }
    for key, cat in mapping.items():
        if key in source_type:
            return cat
    et = str(mention.get("entity_type") or "").lower()
    if et in ("telegram", "forum", "news", "social"):
        return et
    return "search"


class RegistryIntelligenceEngine(IntelligenceEngine):
    kind = EngineKind.REGISTRY
    title_ru = "Registry Intelligence Engine"
    maturity = "production"

    def analyze(self, ctx: IntelligenceContext) -> EngineAnalysisResult:
        findings: list[IntelligenceFinding] = []
        labels = (ctx.attribution or {}).get("labels") or {}
        registry_sources = ("sovereign_registry", "rosfin", "registry", "ofac", "opensanctions", "graphsense")

        for addr, lbl in labels.items():
            if not isinstance(lbl, dict):
                continue
            src = str(lbl.get("source") or "").lower()
            if not any(r in src for r in registry_sources):
                continue
            findings.append(
                IntelligenceFinding(
                    engine=self.kind,
                    code="REGISTRY_LABEL",
                    title_ru="Запись реестра",
                    description_ru=f"{lbl.get('label', '—')} · источник {src}.",
                    confidence=float(lbl.get("confidence") or 0.8),
                    severity="medium" if lbl.get("sanctioned") else "info",
                    entity_type="company" if lbl.get("category") == "exchange" else "blockchain_address",
                    entity_value=addr,
                    explain={"source": src, "tier": lbl.get("tier")},
                )
            )

        conf = calculate_confidence(
            sources=["registry"] * max(1, len(findings)),
            base_confidence=0.9,
        )
        return EngineAnalysisResult(engine=self.kind, findings=findings, confidence=conf)


class BehavioralIntelligenceEngine(IntelligenceEngine):
    kind = EngineKind.BEHAVIORAL
    title_ru = "Behavioral Intelligence Engine"
    maturity = "production"

    def analyze(self, ctx: IntelligenceContext) -> EngineAnalysisResult:
        findings: list[IntelligenceFinding] = []
        onchain = (ctx.screening or {}).get("onchain_summary") or {}
        inbound = float(onchain.get("inbound_amount") or 0)
        outbound = float(onchain.get("outbound_amount") or 0)
        in_n = int(onchain.get("inbound_count") or 0)
        out_n = int(onchain.get("outbound_count") or 0)

        if in_n and out_n and abs(inbound - outbound) / max(inbound, 1) < 0.05:
            findings.append(
                IntelligenceFinding(
                    engine=self.kind,
                    code="BEHAVIOR_PASS_THROUGH",
                    title_ru="Гипотеза: транзитный поток",
                    description_ru="Входящий и исходящий объём близки — типичный pass-through.",
                    confidence=0.65,
                    severity="medium",
                    entity_type="blockchain_address",
                    entity_value=ctx.address,
                    explain={"behavioral": "temporal_volume_match"},
                )
            )

        if out_n > in_n * 3 and out_n > 10:
            findings.append(
                IntelligenceFinding(
                    engine=self.kind,
                    code="BEHAVIOR_DISPERSION",
                    title_ru="Гипотеза: дробление исходящих",
                    description_ru=f"Исходящих транзакций ({out_n}) значительно больше входящих ({in_n}).",
                    confidence=0.6,
                    severity="medium",
                    entity_type="blockchain_address",
                    entity_value=ctx.address,
                    explain={"behavioral": "dispersion"},
                )
            )

        for signal in temporal_correlation_signals(ctx.mentions):
            findings.append(
                IntelligenceFinding(
                    engine=self.kind,
                    code="BEHAVIOR_TEMPORAL",
                    title_ru="Временная корреляция OSINT",
                    description_ru=f"Упоминаний в окне {signal.get('span_hours')} ч: {signal.get('mention_count')}.",
                    confidence=float(signal.get("confidence") or 0.65),
                    severity="medium",
                    entity_type="blockchain_address",
                    entity_value=ctx.address,
                    explain=signal,
                )
            )

        for corridor in corridor_hints(ctx.screening):
            findings.append(
                IntelligenceFinding(
                    engine=self.kind,
                    code="CORRIDOR_MATCH",
                    title_ru="Коридор перемещения средств",
                    description_ru=f"Регионы: {', '.join(corridor.get('matched_regions') or [])}.",
                    confidence=float(corridor.get("confidence") or 0.7),
                    severity="medium",
                    entity_type="blockchain_address",
                    entity_value=ctx.address,
                    explain=corridor,
                )
            )

        conf = calculate_confidence(sources=["blockchain_explorer"], base_confidence=0.7)
        return EngineAnalysisResult(engine=self.kind, findings=findings, confidence=conf)


class EntityResolutionIntelligenceEngine(IntelligenceEngine):
    kind = EngineKind.ENTITY_RESOLUTION
    title_ru = "Entity Resolution Engine"
    maturity = "production"

    def analyze(self, ctx: IntelligenceContext) -> EngineAnalysisResult:
        from flowsint_crypto_compliance.platform.v2.entity_resolution import EntityResolutionEngine

        findings: list[IntelligenceFinding] = []
        if ctx.address and ctx.chain:
            resolver = EntityResolutionEngine()
            res = resolver.resolve_with_scoring(
                tenant_id=ctx.tenant_id,
                entity_type="blockchain_address",
                value=ctx.address,
                chain=ctx.chain,
                source="intelligence.er",
            )
            findings.append(
                IntelligenceFinding(
                    engine=self.kind,
                    code="ER_DECISION",
                    title_ru="Решение Entity Resolution",
                    description_ru=f"Решение: {res.decision.value}, уверенность {res.confidence:.2f}.",
                    confidence=res.confidence,
                    severity="info",
                    entity_type="blockchain_address",
                    entity_value=ctx.address,
                    explain=res.explain,
                )
            )
        conf = calculate_confidence(sources=["identifier"], base_confidence=0.85)
        return EngineAnalysisResult(engine=self.kind, findings=findings, confidence=conf, explain={"delegates_to": "platform/v2/entity_resolution.py"})


class CorrelationIntelligenceEngine(IntelligenceEngine):
    kind = EngineKind.CORRELATION
    title_ru = "Correlation Engine"
    maturity = "production"

    def analyze(self, ctx: IntelligenceContext) -> EngineAnalysisResult:
        findings: list[IntelligenceFinding] = []
        seen_values: dict[str, list[str]] = {}

        for m in ctx.mentions:
            if not isinstance(m, dict):
                continue
            for key in ("phone", "email", "domain", "username"):
                val = m.get(key) or (m.get("entity_value") if m.get("entity_type") == key else None)
                if val:
                    seen_values.setdefault(key, []).append(str(val))

        for neighbor in ctx.kg_neighbors:
            rel = neighbor.get("relation_type") or neighbor.get("type")
            nid = neighbor.get("entity_id") or neighbor.get("id")
            if rel and nid:
                findings.append(
                    IntelligenceFinding(
                        engine=self.kind,
                        code="KG_CORRELATION",
                        title_ru="Корреляция в графе",
                        description_ru=f"Связь {rel} с сущностью {str(nid)[:8]}…",
                        confidence=float(neighbor.get("confidence") or 0.6),
                        severity="info",
                        explain={"relation_type": rel, "neighbor": neighbor},
                    )
                )

        for key, vals in seen_values.items():
            unique = set(vals)
            if len(unique) < len(vals):
                findings.append(
                    IntelligenceFinding(
                        engine=self.kind,
                        code="SHARED_IDENTIFIER",
                        title_ru="Общий идентификатор",
                        description_ru=f"Повторяющийся {key} в OSINT-упоминаниях.",
                        confidence=0.72,
                        severity="medium",
                        explain={"identifier_type": key, "values": list(unique)[:5]},
                    )
                )

        for signal in temporal_correlation_signals(ctx.mentions):
            findings.append(
                IntelligenceFinding(
                    engine=self.kind,
                    code="TEMPORAL_CORRELATION",
                    title_ru="Временной кластер упоминаний",
                    description_ru=f"{signal.get('mention_count')} упоминаний за {signal.get('span_hours')} ч.",
                    confidence=float(signal.get("confidence") or 0.7),
                    severity="medium",
                    explain=signal,
                )
            )

        prior: list[dict[str, Any]] = (ctx.screening or {}).get("_intel_findings") or []
        engine_codes: dict[str, list[str]] = {}
        for raw in prior:
            eng = str(raw.get("engine") or "")
            code = str(raw.get("code") or "")
            if eng and code:
                engine_codes.setdefault(eng, []).append(code)
        if len(engine_codes) >= 2:
            findings.append(
                IntelligenceFinding(
                    engine=self.kind,
                    code="CROSS_ENGINE_CORRELATION",
                    title_ru="Междусистемная корреляция",
                    description_ru=f"Согласованные сигналы из {len(engine_codes)} движков.",
                    confidence=0.75,
                    severity="medium",
                    entity_type="blockchain_address",
                    entity_value=ctx.address,
                    explain={"engines": list(engine_codes.keys()), "codes": engine_codes},
                )
            )

        conf = calculate_confidence(
            sources=["osint"] * max(1, len(findings)),
            base_confidence=0.6,
        )
        return EngineAnalysisResult(engine=self.kind, findings=findings, confidence=conf)


class AttributionIntelligenceEngine(IntelligenceEngine):
    kind = EngineKind.ATTRIBUTION
    title_ru = "Attribution Engine"
    maturity = "production"

    def analyze(self, ctx: IntelligenceContext) -> EngineAnalysisResult:
        from flowsint_crypto_compliance.attribution.attribution_engine import AttributionResult

        findings: list[IntelligenceFinding] = []
        attr = AttributionResult.from_dict(ctx.attribution)
        for addr, lbl in attr.labels.items():
            findings.append(
                IntelligenceFinding(
                    engine=self.kind,
                    code="ATTRIBUTION_HYPOTHESIS",
                    title_ru="Гипотеза атрибуции",
                    description_ru=f"{lbl.label} (tier {lbl.tier}, {lbl.category}).",
                    confidence=float(lbl.confidence or 0.5),
                    severity="high" if lbl.sanctioned else "medium",
                    entity_type="blockchain_address",
                    entity_value=addr,
                    explain={"tier": lbl.tier, "source": lbl.source, "sanctioned": lbl.sanctioned},
                )
            )
        for hit in attr.sanctions_hits:
            findings.append(
                IntelligenceFinding(
                    engine=self.kind,
                    code="SANCTIONS_HIT",
                    title_ru="Попадание в санкционный список",
                    description_ru=str(hit.get("name") or hit.get("label") or "sanctions"),
                    confidence=float(hit.get("confidence") or 0.9),
                    severity="critical",
                    explain=hit,
                )
            )
        srcs = ["sanctions"] * len(attr.sanctions_hits) if attr.sanctions_hits else ["registry"]
        conf = calculate_confidence(sources=srcs, base_confidence=0.7 if not attr.sanctions_hits else 0.9)
        return EngineAnalysisResult(engine=self.kind, findings=findings, confidence=conf)


class RiskIntelligenceEngine(IntelligenceEngine):
    kind = EngineKind.RISK
    title_ru = "Risk Engine"
    maturity = "production"

    def analyze(self, ctx: IntelligenceContext) -> EngineAnalysisResult:
        """Aggregates prior engine findings passed via ctx.screening['_intel_findings']."""
        findings: list[IntelligenceFinding] = []
        prior: list[dict[str, Any]] = (ctx.screening or {}).get("_intel_findings") or []
        base_score = float((ctx.screening or {}).get("risk_score") or 0)

        weights = {"critical": 25, "high": 15, "medium": 8, "info": 2}
        boost = 0.0
        explain_factors: list[dict[str, Any]] = []

        for raw in prior:
            sev = str(raw.get("severity") or "info")
            conf = float(raw.get("confidence") or 0.5)
            w = weights.get(sev, 2) * conf
            boost += w
            explain_factors.append({"code": raw.get("code"), "severity": sev, "weight": round(w, 2)})

        illegal_boost, illegal_explain = illegal_flow_risk_boost(
            ctx.screening or {},
            ctx.attribution or {},
        )
        if illegal_boost > 0:
            boost += illegal_boost
            explain_factors.append(
                {"code": "ILLEGAL_FLOW", "severity": "high", "weight": round(illegal_boost, 2)}
            )

        aggregate = min(100.0, base_score + boost)
        level = "low"
        if aggregate >= 75:
            level = "critical"
        elif aggregate >= 55:
            level = "high"
        elif aggregate >= 35:
            level = "medium"

        findings.append(
            IntelligenceFinding(
                engine=self.kind,
                code="AGGREGATE_RISK",
                title_ru="Интегральный риск",
                description_ru=f"Оценка {aggregate:.1f}/100 ({level}).",
                confidence=min(1.0, aggregate / 100.0),
                severity=level if level != "low" else "info",
                entity_type="blockchain_address",
                entity_value=ctx.address,
                explain={
                    "base_score": base_score,
                    "boost": boost,
                    "illegal_flow_boost": illegal_boost,
                    "factors": explain_factors,
                    "risk_level": level,
                    "illegal_flow": illegal_explain,
                },
            )
        )
        conf = calculate_confidence(
            sources=["registry"] * max(1, len(prior)),
            base_confidence=aggregate / 100.0,
        )
        return EngineAnalysisResult(
            engine=self.kind,
            findings=findings,
            confidence=conf,
            explain={
                "aggregate_risk_score": aggregate,
                "risk_level": level,
                "illegal_flow_boost": illegal_boost,
            },
        )


class TimelineIntelligenceEngine(IntelligenceEngine):
    kind = EngineKind.TIMELINE
    title_ru = "Timeline Engine"
    maturity = "production"

    def analyze(self, ctx: IntelligenceContext) -> EngineAnalysisResult:
        findings: list[IntelligenceFinding] = []
        events = ctx.timeline_events
        if ctx.case_ref and not events:
            try:
                from flowsint_crypto_compliance.platform.v2.gateway import case_timeline

                events = case_timeline(ctx.case_ref, limit=50).get("events") or []
            except Exception:
                events = []

        if events:
            findings.append(
                IntelligenceFinding(
                    engine=self.kind,
                    code="TIMELINE_READY",
                    title_ru="Временная шкала расследования",
                    description_ru=f"Событий в журнале: {len(events)}.",
                    confidence=0.95,
                    severity="info",
                    explain={"event_count": len(events), "latest": events[0] if events else None},
                )
            )
        conf = calculate_confidence(sources=["registry"], base_confidence=0.9)
        return EngineAnalysisResult(engine=self.kind, findings=findings, confidence=conf)


class ExplainIntelligenceEngine(IntelligenceEngine):
    kind = EngineKind.EXPLAIN
    title_ru = "Explainable AI Engine"
    maturity = "production"

    def analyze(self, ctx: IntelligenceContext) -> EngineAnalysisResult:
        prior: list[dict[str, Any]] = (ctx.screening or {}).get("_intel_findings") or []
        prior_results: list[dict[str, Any]] = (ctx.screening or {}).get("_intel_engine_results") or []

        rules_fired = [f.get("code") for f in prior if f.get("code")]
        models = [r.get("engine") for r in prior_results if r.get("engine")]
        alt: list[str] = []
        if any(f.get("code") == "BEHAVIOR_PASS_THROUGH" for f in prior):
            alt.append("Легитимный OTC-канал с быстрым оборотом")
        if any(f.get("code") in ("MIXER_OR_SANCTIONS", "MIXER_DETECTED") for f in prior):
            alt.append("Прямое взаимодействие с санкционным/миксерным контрагентом")

        findings = [
            IntelligenceFinding(
                engine=self.kind,
                code="EXPLAIN_BUNDLE",
                title_ru="Объяснение выводов",
                description_ru=f"Правил: {len(rules_fired)}, движков: {len(models)}.",
                confidence=0.9,
                severity="info",
                explain={
                    "data_used": ["knowledge_graph", "screening", "attribution", "mentions"],
                    "rules_fired": rules_fired[:20],
                    "models_applied": models,
                    "alternative_explanations_ru": alt,
                },
            )
        ]
        conf = calculate_confidence(sources=["registry"], base_confidence=0.85)
        return EngineAnalysisResult(engine=self.kind, findings=findings, confidence=conf, explain=findings[0].explain)


class RecommendationIntelligenceEngine(IntelligenceEngine):
    kind = EngineKind.RECOMMENDATION
    title_ru = "Investigation Recommendation Engine"
    maturity = "production"

    def analyze(self, ctx: IntelligenceContext) -> EngineAnalysisResult:
        recs: list[dict[str, Any]] = []
        risk = float((ctx.screening or {}).get("_aggregate_risk") or (ctx.screening or {}).get("risk_score") or 0)
        prior: list[dict[str, Any]] = (ctx.screening or {}).get("_intel_findings") or []

        if risk >= 55:
            recs.append({"action_ru": "Запросить дополнительные банковские документы", "priority": "high"})
        if not ctx.mentions:
            recs.append({"action_ru": "Выполнить повторный OSINT-поиск", "priority": "medium"})
        if any(f.get("code") == "SHARED_IDENTIFIER" for f in prior):
            recs.append({"action_ru": "Проверить связанные организации по общим идентификаторам", "priority": "high"})
        if any(f.get("code") in ("MIXER_OR_SANCTIONS", "MIXER_DETECTED") for f in prior):
            recs.append({"action_ru": "Сформировать отчёт для регулятора (115-ФЗ)", "priority": "critical"})
        if any(f.get("code") in ("BEHAVIOR_TEMPORAL", "TEMPORAL_CORRELATION") for f in prior):
            recs.append({"action_ru": "Исследовать определённый временной период", "priority": "medium"})
        if len(prior) < 3:
            recs.append({"action_ru": "Импортировать данные из нового источника", "priority": "medium"})
        recs.append({"action_ru": "Построить граф финансовых потоков", "priority": "medium"})
        if ctx.case_ref:
            recs.append({
                "action_ru": "Сформировать отчёт",
                "priority": "medium",
                "href": f"/api/compliance/cases/{ctx.case_ref}/report.json",
            })

        findings = [
            IntelligenceFinding(
                engine=self.kind,
                code="INVESTIGATION_RECOMMENDATIONS",
                title_ru="Рекомендации аналитику",
                description_ru=f"Предложено шагов: {len(recs)}.",
                confidence=0.85,
                severity="info",
                explain={"recommendations": recs},
            )
        ]
        conf = calculate_confidence(sources=["registry"], base_confidence=0.8)
        return EngineAnalysisResult(engine=self.kind, findings=findings, confidence=conf, explain={"recommendations": recs})
