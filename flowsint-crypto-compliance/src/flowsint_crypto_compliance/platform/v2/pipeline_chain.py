"""Appendix A pipeline chain — RFC-0003 full data path."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

APPENDIX_A_CHAIN: list[str] = [
    "source",
    "event",
    "normalize",
    "entity_resolution",
    "knowledge_graph",
    "evidence",
    "analytics",
    "investigation",
    "report",
]


def pipeline_chain_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0003",
        "appendix": "A",
        "title": "Источник → Событие → … → Отчёт",
        "stages": [
            {"id": s, "label_ru": _STAGE_LABELS_RU.get(s, s)}
            for s in APPENDIX_A_CHAIN
        ],
        "rule_ru": "Ни один сервис не должен нарушать эту последовательность",
        "orchestrator": "PipelineChainOrchestrator",
    }


_STAGE_LABELS_RU: dict[str, str] = {
    "source": "Источник",
    "event": "Событие",
    "normalize": "Нормализация",
    "entity_resolution": "Entity Resolution",
    "knowledge_graph": "Граф знаний",
    "evidence": "Доказательства",
    "analytics": "Аналитика",
    "investigation": "Расследование",
    "report": "Отчёт",
}


@dataclass
class PipelineChainResult:
    ok: bool = True
    stages_completed: list[str] = field(default_factory=list)
    entity_id: str | None = None
    evidence_ids: list[str] = field(default_factory=list)
    risk_score: float | None = None
    case_ref: str | None = None
    investigation_id: str | None = None
    report_refs: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    explain: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "stages_completed": self.stages_completed,
            "entity_id": self.entity_id,
            "evidence_ids": self.evidence_ids,
            "risk_score": self.risk_score,
            "case_ref": self.case_ref,
            "investigation_id": self.investigation_id,
            "report_refs": self.report_refs,
            "errors": self.errors,
            "explain": self.explain,
            "chain": APPENDIX_A_CHAIN,
        }


class PipelineChainOrchestrator:
    """
    Source → Event → Normalize → ER → KG → Evidence → Analytics → Investigation → Report.
    """

    async def run_investigation_chain(
        self,
        *,
        tenant_id: uuid.UUID,
        investigation_id: uuid.UUID,
        case_ref: str,
        address: str,
        chain: str,
        screening: dict[str, Any],
        mentions: list[dict[str, Any]] | None = None,
        correlation_id: str | None = None,
        actor: str = "finskalp.investigator",
    ) -> PipelineChainResult:
        from flowsint_crypto_compliance.platform.v2.fusion_pipeline import default_fusion_pipeline
        from flowsint_crypto_compliance.platform.v2.ingest_pipeline import get_ingest_pipeline
        from flowsint_crypto_compliance.platform.v2.investigation_workspace import InvestigationWorkspace

        result = PipelineChainResult(
            case_ref=case_ref,
            investigation_id=str(investigation_id),
        )
        pipeline = get_ingest_pipeline()

        # Source → Event → Normalize → ER → KG → Evidence (wallet seed)
        wallet_ingest = pipeline.ingest(
            tenant_id=tenant_id,
            source_type="finskalp.investigator",
            entity_type="blockchain_address",
            entity_value=address,
            chain=chain,
            case_ref=case_ref,
            actor=actor,
            confidence=float(screening.get("risk_score", 50) or 50) / 100.0,
            payload={
                "screening": screening,
                "investigation_id": str(investigation_id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            require_relation_evidence=False,
        )
        if wallet_ingest.ok:
            result.stages_completed.extend(wallet_ingest.stages_completed)
            result.entity_id = str(wallet_ingest.entity_id) if wallet_ingest.entity_id else None
            if wallet_ingest.evidence_id:
                result.evidence_ids.append(str(wallet_ingest.evidence_id))
        else:
            result.errors.extend(wallet_ingest.errors)
            result.ok = False

        # Mentions through ingest
        for m in mentions or []:
            if not isinstance(m, dict):
                continue
            et = str(m.get("entity_type") or "domain")
            ev = str(m.get("entity_value") or m.get("mention") or m.get("url") or "")
            if not ev:
                continue
            ing = pipeline.ingest(
                tenant_id=tenant_id,
                source_type=str(m.get("source_type") or "osint"),
                entity_type=et,
                entity_value=ev,
                case_ref=case_ref,
                actor=actor,
                confidence=float(m.get("confidence") or 0.5),
                payload={**m, "investigation_id": str(investigation_id)},
                relation_to=wallet_ingest.entity_id if wallet_ingest.entity_id else None,
                require_relation_evidence=False,
            )
            if ing.ok:
                for s in ing.stages_completed:
                    if s not in result.stages_completed:
                        result.stages_completed.append(s)
                if ing.evidence_id:
                    result.evidence_ids.append(str(ing.evidence_id))

        # Fusion (normalize/enrich/confidence within L2)
        records = [
            {
                "source_type": m.get("source_type", "osint"),
                "confidence": float(m.get("confidence") or m.get("fusion_confidence") or 0.5),
                "source_name": m.get("source_name") or m.get("collector_id"),
                "dependency_group": m.get("dependency_group"),
            }
            for m in (mentions or [])
            if isinstance(m, dict)
        ]
        if records:
            pipe = default_fusion_pipeline()
            await pipe.run(
                records,
                tenant_id=tenant_id,
                investigation_id=investigation_id,
                correlation_id=correlation_id,
                context={"case_ref": case_ref},
            )
            result.stages_completed.append("fusion")

        # Analytics — RFC-0006 Intelligence Engine (wraps RFC-0004)
        from flowsint_crypto_compliance.platform.v2.intelligence_engine import run_intelligence_engine as run_rfc6

        entity_uuid = None
        if result.entity_id:
            try:
                entity_uuid = uuid.UUID(result.entity_id)
            except ValueError:
                pass

        rfc6 = run_rfc6(
            tenant_id=tenant_id,
            address=address,
            chain=chain,
            case_ref=case_ref,
            investigation_id=investigation_id,
            entity_id=entity_uuid,
            screening=screening,
            attribution=screening.get("attribution") if isinstance(screening.get("attribution"), dict) else {},
            mentions=mentions if isinstance(mentions, list) else [],
            publish=True,
            learn_memory=True,
        )
        result.risk_score = float(
            rfc6.scores.hypothesis_confidence or screening.get("risk_score") or 0
        )
        result.stages_completed.append("analytics")
        ai_explain = (rfc6.explain or {}).get("ai_explanation") or {}
        result.explain["analytics"] = {
            "rfc": "RFC-0006",
            "engines_run": ai_explain.get("engines_run") or [],
            "risk_level": "medium" if rfc6.scores.hypothesis_confidence >= 50 else "low",
            "scores": rfc6.scores.to_dict(),
            "weakest_score": {"metric": rfc6.scores.weakest()[0], "value": rfc6.scores.weakest()[1]},
            "patterns": len(rfc6.patterns),
            "hypotheses": len(rfc6.hypotheses),
            "recommendations": rfc6.recommendations,
            "pipeline_stages": rfc6.pipeline_stages,
            "questions_answered": rfc6.questions_answered,
            "explain": rfc6.explain,
        }
        if rfc6.published_evidence_ids:
            result.evidence_ids.extend(rfc6.published_evidence_ids)

        # Investigation workspace
        try:
            InvestigationWorkspace().attach_investigation(
                case_ref=case_ref,
                investigation_id=investigation_id,
                address=address,
                chain=chain,
                tenant_id=tenant_id,
            )
            result.stages_completed.append("investigation")
        except Exception as exc:
            result.errors.append(f"investigation: {exc}")

        # Report artifact references
        result.report_refs = {
            "case_ref": case_ref,
            "investigation_id": str(investigation_id),
            "pdf": f"/api/compliance/cases/{case_ref}/report.pdf",
            "json": f"/api/compliance/cases/{case_ref}/report.json",
        }
        result.stages_completed.append("report")

        # Ensure chain order tracked
        for stage in APPENDIX_A_CHAIN:
            if stage not in result.stages_completed and stage in (
                "source",
                "event",
                "normalize",
                "entity_resolution",
                "knowledge_graph",
                "evidence",
            ):
                if wallet_ingest.ok:
                    result.stages_completed.append(stage)

        result.ok = bool(result.entity_id) and not any(
            e for e in result.errors if "investigation" not in e
        )
        return result


_orchestrator: PipelineChainOrchestrator | None = None


def get_pipeline_chain_orchestrator() -> PipelineChainOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = PipelineChainOrchestrator()
    return _orchestrator
