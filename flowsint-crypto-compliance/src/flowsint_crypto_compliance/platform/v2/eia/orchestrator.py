"""RFC-0018 Ch.1 — EIA orchestrator (read-only, human-in-the-loop)."""

from __future__ import annotations

import uuid
from typing import Any

from flowsint_crypto_compliance.platform.v2.eia.constraints import eia_architectural_constraints
from flowsint_crypto_compliance.platform.v2.eia.context_engine import build_investigation_context
from flowsint_crypto_compliance.platform.v2.eia.evidence_assistant import build_evidence_summary
from flowsint_crypto_compliance.platform.v2.eia.explanation_engine import explain_links, explain_risk
from flowsint_crypto_compliance.platform.v2.eia.graph_assistant import build_graph_narrative
from flowsint_crypto_compliance.platform.v2.eia.model_registry import get_llm_provider
from flowsint_crypto_compliance.platform.v2.eia.monitoring import LatencyTimer, get_eia_metrics
from flowsint_crypto_compliance.platform.v2.eia.prompt_engine import render_prompt
from flowsint_crypto_compliance.platform.v2.eia.recommendation_engine import build_recommendations
from flowsint_crypto_compliance.platform.v2.eia.report_assistant import build_report_outline
from flowsint_crypto_compliance.platform.v2.eia.security import append_audit_entry
from flowsint_crypto_compliance.platform.v2.eia.summary_engine import build_investigation_brief
from flowsint_crypto_compliance.platform.v2.eia.timeline_assistant import build_timeline_analysis
from flowsint_crypto_compliance.platform.v2.eia.types import AITaskType, AssistantResponse, Citation, EIAStage


async def run_eia_task(
    *,
    task_type: str | AITaskType,
    case_ref: str,
    entity_keys: list[str] | None = None,
    tenant_id: uuid.UUID | None = None,
    actor: str = "eia.orchestrator",
    prompt_version: str | None = None,
) -> AssistantResponse:
    """
    Main EIA entry — wires context/prompt/explanation/recommendation/summary engines.
    MUST NOT mutate KG/evidence/risk or make final decisions.
    """
    if isinstance(task_type, AITaskType):
        task_type_str = task_type.value
    else:
        task_type_str = str(task_type)

    constraints = eia_architectural_constraints()
    keys = entity_keys or []
    result = AssistantResponse(
        ok=True,
        task_type=task_type_str,
        case_ref=case_ref,
        entity_keys=keys,
        requires_analyst_confirmation=True,
    )
    stages: list[str] = []
    metrics = get_eia_metrics()
    cache_hit = False

    with LatencyTimer() as timer:
        try:
            # Stage 1: Context
            context = await build_investigation_context(
                case_ref=case_ref,
                entity_keys=keys,
                tenant_id=tenant_id,
            )
            cache_hit = context.get("cache_hit", False)
            stages.append(EIAStage.CONTEXT.value)
            result.explain["context_sources"] = context.get("sources", [])

            # Stage 2: Prompt
            prompt_context = _build_prompt_context(task_type_str, case_ref, keys, context)
            prompt_result = render_prompt(task_type_str, prompt_context, version=prompt_version)
            stages.append(EIAStage.PROMPT.value)
            result.explain["prompt"] = {
                "version": prompt_result.get("version"),
                "ok": prompt_result.get("ok"),
            }

            # Stage 3: Model (optional LLM enrichment)
            model_narrative = ""
            if prompt_result.get("ok") and prompt_result.get("prompt"):
                model = get_llm_provider()
                model_narrative = model.complete(prompt_result["prompt"])
            stages.append(EIAStage.MODEL.value)

            # Stage 4: Task-specific engine
            engine_result = _run_task_engine(task_type_str, case_ref, keys, context)
            stages.append(EIAStage.EXPLANATION.value)

            result.narrative_ru = engine_result.get("narrative_ru") or model_narrative
            if model_narrative and engine_result.get("narrative_ru"):
                result.narrative_ru = f"{engine_result['narrative_ru']} {model_narrative}"

            raw_citations = engine_result.get("citations") or []
            result.citations = [
                c if isinstance(c, Citation) else Citation(**c) for c in raw_citations
            ] if raw_citations and isinstance(raw_citations[0], Citation) else [
                Citation(
                    evidence_id=c.get("evidence_id"),
                    source_type=c.get("source_type", "unknown"),
                    label_ru=c.get("label_ru", ""),
                    confidence=c.get("confidence", 0.0),
                    excerpt=c.get("excerpt"),
                )
                for c in raw_citations
            ]
            result.confidence = engine_result.get("confidence", 0.5)
            result.limitations = engine_result.get("limitations") or []
            result.explain["engine"] = {k: v for k, v in engine_result.items() if k != "citations"}

            # Stage 5: Recommendations
            primary_key = keys[0] if keys else None
            result.recommendations = build_recommendations(
                context=context,
                entity_key=primary_key,
                task_type=task_type_str,
            )
            stages.append(EIAStage.RECOMMENDATION.value)

            # Stage 6: Summary enrichment for summary task
            if task_type_str == AITaskType.SUMMARY.value:
                brief = build_investigation_brief(context)
                result.explain["brief"] = brief.get("brief")
            stages.append(EIAStage.SUMMARY.value)

            # Stage 7: Deliver
            result.stages = stages
            result.explain["constraints"] = constraints
            stages.append(EIAStage.DELIVER.value)
            result.stages = stages

            append_audit_entry(
                action="eia_task_complete",
                actor=actor,
                case_ref=case_ref,
                task_type=task_type_str,
                details={"entity_keys": keys, "confidence": result.confidence},
            )

            metrics.record_task(
                task_type=task_type_str,
                latency_ms=timer.elapsed_ms,
                ok=result.ok,
                cache_hit=cache_hit,
            )

        except Exception as exc:
            result.ok = False
            result.errors.append(str(exc))
            result.stages = stages
            metrics.record_task(
                task_type=task_type_str,
                latency_ms=timer.elapsed_ms,
                ok=False,
                cache_hit=cache_hit,
            )

    return result


def _build_prompt_context(
    task_type: str,
    case_ref: str,
    entity_keys: list[str],
    context: dict[str, Any],
) -> dict[str, Any]:
    primary = entity_keys[0] if entity_keys else ""
    rde = (context.get("rde_assessments") or {}).get(primary) or {}
    return {
        "case_ref": case_ref,
        "entity_key": primary,
        "entity_keys": ", ".join(entity_keys),
        "context_summary": f"stage={context.get('case', {}).get('workflow_stage')}, evidence={context.get('evidence_count', 0)}",
        "risk_signals": str(rde.get("signals") or {}),
        "top_factors": str((rde.get("explanation") or {}).get("why", {}).get("top_factors") or []),
        "neighbors": str((context.get("neighbors") or {}).get(primary) or []),
        "hypotheses": str(context.get("hypotheses") or []),
        "evidence_count": str(context.get("evidence_count", 0)),
        "timeline_events": str(len(context.get("timeline") or [])),
        "sources": str(context.get("sources") or []),
        "acquired_groups": str(list((rde.get("signals") or {}).keys())),
        "missing_groups": str((rde.get("explanation") or {}).get("missing") or []),
    }


def _run_task_engine(
    task_type: str,
    case_ref: str,
    entity_keys: list[str],
    context: dict[str, Any],
) -> dict[str, Any]:
    primary = entity_keys[0] if entity_keys else ""

    if task_type == AITaskType.SUMMARY.value:
        return build_investigation_brief(context)

    if task_type == AITaskType.EXPLAIN_RISK.value:
        if not primary:
            return {"narrative_ru": "Укажите объект для объяснения риска.", "confidence": 0.0, "limitations": []}
        return explain_risk(entity_key=primary, context=context)

    if task_type == AITaskType.DESCRIBE_LINKS.value:
        if not primary:
            return {"narrative_ru": "Укажите объект для описания связей.", "confidence": 0.0, "limitations": []}
        return explain_links(entity_key=primary, context=context)

    if task_type == AITaskType.QUESTIONS.value:
        hyps = context.get("hypotheses") or []
        questions = [f"Подтвердить: {h.get('statement_ru', '')}" for h in hyps[:5]]
        if not questions:
            questions = ["Какие объекты являются ключевыми в деле?", "Достаточно ли доказательной базы?"]
        return {
            "narrative_ru": f"Открытые вопросы по делу {case_ref}: " + "; ".join(questions[:3]),
            "questions": questions,
            "confidence": 0.5,
            "limitations": ["Вопросы сформулированы EIA — требуют оценки аналитика"],
        }

    if task_type == AITaskType.REPORT_OUTLINE.value:
        return build_report_outline(context)

    if task_type == AITaskType.EXPLAIN_CHANGES.value:
        return build_timeline_analysis(context)

    if task_type == AITaskType.CONTRADICTIONS.value:
        return _analyze_contradictions(context)

    if task_type == AITaskType.DATA_GAPS.value:
        return _analyze_data_gaps(entity_keys, context)

    # Graph narrative fallback
    if entity_keys:
        return build_graph_narrative(entity_keys=entity_keys, context=context)

    return build_investigation_brief(context)


def _analyze_contradictions(context: dict[str, Any]) -> dict[str, Any]:
    sources = context.get("sources") or []
    contradictions = []
    assessments = context.get("rde_assessments") or {}
    levels = set()
    for assess in assessments.values():
        level = (assess.get("risk_mapping") or {}).get("risk_level")
        if level:
            levels.add(level)
    if len(levels) > 1:
        contradictions.append(f"Разные уровни риска для объектов: {', '.join(levels)}")

    narrative = (
        f"Потенциальных противоречий: {len(contradictions)}. "
        + ("; ".join(contradictions) if contradictions else "Явных противоречий не обнаружено.")
    )
    return {
        "narrative_ru": narrative,
        "contradictions": contradictions,
        "confidence": 0.4,
        "limitations": ["Анализ противоречий эвристический"],
        "sources_checked": sources,
    }


def _analyze_data_gaps(entity_keys: list[str], context: dict[str, Any]) -> dict[str, Any]:
    primary = entity_keys[0] if entity_keys else ""
    rde = (context.get("rde_assessments") or {}).get(primary) or {}
    missing = (rde.get("explanation") or {}).get("missing") or []
    if not missing:
        missing = ["blockchain", "registry"] if not context.get("evidence") else []

    narrative = f"Пробелы в данных: {', '.join(missing) if missing else 'не выявлены'}."
    return {
        "narrative_ru": narrative,
        "missing_groups": missing,
        "confidence": 0.5,
        "limitations": ["Список пробелов основан на доступных сигналах RDE"],
    }
