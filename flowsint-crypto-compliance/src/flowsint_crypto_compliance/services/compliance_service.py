from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from flowsint_crypto_compliance.ingestion.bank_regulator import bank_feed_to_fiat_event
from flowsint_crypto_compliance.ingestion.registry_staging import stage_registry_lines
from flowsint_crypto_compliance.ingestion.sovereign_registry import parse_registry_row
from flowsint_crypto_compliance.osint_core.fusion_engine import (
    InvestigationBundle,
    OSINTFusionEngine,
)
from flowsint_crypto_compliance.schemas.hub import hub_row_to_bank_feed, validate_bank_feed_batch
from flowsint_crypto_compliance.storage.db_models import (
    ComplianceAuditLog,
    ComplianceBankFeed,
    ComplianceCase,
    ComplianceCaseComment,
    ComplianceFusionRun,
    OsintFinding,
)
from flowsint_crypto_compliance.storage.neo4j_exporter import EvidenceGraphNeo4jExporter
from flowsint_crypto_compliance.platform.v2.neo4j_projection import project_evidence_graph
from flowsint_crypto_compliance.storage.cache_factory import build_label_cache
from flowsint_crypto_compliance.storage.neo4j_pivots import ComplianceNeo4jPivotExporter
from flowsint_crypto_compliance.services.graph_timestamps import enrich_serialized_graph

class ComplianceService:
    """Persistence + fusion orchestration for regulator compliance cases."""

    def __init__(self, db: Session):
        self._db = db
        self._cache = build_label_cache(db)

    def create_case(
        self,
        *,
        case_ref: str,
        owner_id: uuid.UUID,
        investigation_id: uuid.UUID | None = None,
    ) -> ComplianceCase:
        case = ComplianceCase(
            case_ref=case_ref,
            owner_id=owner_id,
            investigation_id=investigation_id,
            status="draft",
            workflow_status="new",
        )
        from flowsint_crypto_compliance.services.case_workflow import sla_due_at

        case.due_at = sla_due_at("new")
        self._db.add(case)
        self._db.commit()
        self._db.refresh(case)
        self.log_audit(
            case_id=case.id,
            actor_id=owner_id,
            action="case_created",
            payload={"case_ref": case_ref},
        )
        self._db.commit()
        try:
            from flowsint_crypto_compliance.platform.v2.investigation_workspace import InvestigationWorkspace

            InvestigationWorkspace().bridge_compliance_case(case, actor=str(owner_id))
        except Exception:
            pass
        return case

    def get_case(self, case_id: uuid.UUID) -> ComplianceCase | None:
        return self._db.get(ComplianceCase, case_id)

    def get_case_by_ref(self, case_ref: str) -> ComplianceCase | None:
        return (
            self._db.query(ComplianceCase)
            .filter(ComplianceCase.case_ref == case_ref)
            .first()
        )

    def ingest_bank_feed_batch(self, case_id: uuid.UUID, payload: dict[str, Any]) -> int:
        validate_bank_feed_batch(payload)
        case = self.get_case(case_id)
        if not case:
            raise ValueError("Case not found")

        count = 0
        for row in payload["feeds"]:
            row = dict(row)
            row.setdefault("case_id", case.case_ref)
            feed_id = str(row["feed_id"])
            existing = (
                self._db.query(ComplianceBankFeed)
                .filter(
                    ComplianceBankFeed.case_id == case_id,
                    ComplianceBankFeed.feed_id == feed_id,
                )
                .first()
            )
            if existing:
                existing.payload = row
            else:
                self._db.add(
                    ComplianceBankFeed(
                        case_id=case_id,
                        feed_id=feed_id,
                        payload=row,
                    )
                )
            count += 1
        case.status = "ingesting"
        self._db.commit()
        self.log_audit(
            case_id=case_id,
            actor_id=case.owner_id,
            action="bank_feeds_ingested",
            payload={"count": count, "hub_id": payload.get("hub_id")},
        )
        return count

    def import_registry_jsonl_lines(self, lines: list[str]) -> int:
        labels = stage_registry_lines(lines)
        return self._cache.bulk_upsert(labels)

    def import_registry_parquet(self, path: Path) -> int:
        from flowsint_crypto_compliance.ingestion.registry_staging import stage_registry_parquet

        labels = stage_registry_parquet(path)
        return self._cache.bulk_upsert(labels)

    def create_fusion_run(
        self,
        case_id: uuid.UUID,
        *,
        celery_task_id: str | None = None,
        correlation_id: str | None = None,
    ) -> ComplianceFusionRun:
        run = ComplianceFusionRun(
            case_id=case_id,
            celery_task_id=celery_task_id,
            correlation_id=correlation_id,
            status="pending",
        )
        self._db.add(run)
        self._db.commit()
        self._db.refresh(run)
        return run

    def get_fusion_run(self, run_id: uuid.UUID) -> ComplianceFusionRun | None:
        return self._db.get(ComplianceFusionRun, run_id)

    def update_fusion_run(
        self,
        run_id: uuid.UUID,
        *,
        status: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
        celery_task_id: str | None = None,
    ) -> ComplianceFusionRun | None:
        run = self.get_fusion_run(run_id)
        if not run:
            return None
        run.status = status
        if celery_task_id:
            run.celery_task_id = celery_task_id
        if status == "running" and run.started_at is None:
            run.started_at = datetime.now(timezone.utc)
        if status in {"completed", "failed"}:
            run.finished_at = datetime.now(timezone.utc)
        if result is not None:
            run.result = result
        if error is not None:
            run.error = error
        self._db.commit()
        self._db.refresh(run)
        return run

    def log_audit(
        self,
        *,
        action: str,
        case_id: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
        payload: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        publish_event: bool = True,
    ) -> ComplianceAuditLog:
        entry = ComplianceAuditLog(
            case_id=case_id,
            actor_id=actor_id,
            action=action,
            payload=payload,
            correlation_id=correlation_id,
        )
        self._db.add(entry)
        self._db.flush()
        if publish_event:
            self._publish_domain_event(action, case_id, payload, correlation_id)
        return entry

    def _publish_domain_event(
        self,
        action: str,
        case_id: uuid.UUID | None,
        payload: dict[str, Any] | None,
        correlation_id: str | None,
    ) -> None:
        from flowsint_crypto_compliance.infrastructure.compliance_events import get_event_bus
        from flowsint_crypto_compliance.infrastructure.read_models import (
            ComplianceDashboardReadModel,
            invalidate_dashboard_read_model,
        )

        event_type = action
        severity = "info"
        if action in ("fusion_async_failed",):
            severity = "critical"
            event_type = "fusion_failed"
        elif action in ("fusion_completed", "fusion_async_completed"):
            event_type = "fusion_completed"
        elif action == "bank_feeds_ingested":
            event_type = "bank_feed_ingested"
        bus = get_event_bus()
        bus.publish(
            event_type,
            payload=payload,
            severity=severity,
            correlation_id=correlation_id,
        )
        invalidate_dashboard_read_model()
        if self._db:
            try:
                ComplianceDashboardReadModel(self._db).refresh()
            except Exception:
                pass

    def list_audit_log(
        self,
        *,
        case_id: uuid.UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ComplianceAuditLog]:
        q = self._db.query(ComplianceAuditLog).order_by(ComplianceAuditLog.created_at.desc())
        if case_id:
            q = q.filter(ComplianceAuditLog.case_id == case_id)
        return q.offset(offset).limit(min(limit, 500)).all()

    async def fuse_case(
        self,
        case_id: uuid.UUID,
        *,
        licensed_events: list[LicensedPlatformEvent] | None = None,
        control_purchases: list[ControlPurchaseEvent] | None = None,
        chain_adapters: dict | None = None,
    ) -> dict[str, Any]:
        case = self.get_case(case_id)
        if not case:
            raise ValueError("Case not found")

        bank_rows = (
            self._db.query(ComplianceBankFeed)
            .filter(ComplianceBankFeed.case_id == case_id)
            .all()
        )
        bank_feeds = [hub_row_to_bank_feed(r.payload) for r in bank_rows]
        fiat_events = [bank_feed_to_fiat_event(b) for b in bank_feeds]

        engine = OSINTFusionEngine(
            chain_adapters=chain_adapters or {},
            label_cache=self._cache,
        )
        bundle = InvestigationBundle(
            case_id=case.case_ref,
            bank_feeds=bank_feeds,
            fiat_events=fiat_events,
            licensed_events=licensed_events or [],
            control_purchases=control_purchases or [],
        )
        result = await engine.fuse(bundle)

        existing_fr = case.fusion_result if isinstance(case.fusion_result, dict) else {}
        existing_eg = (
            existing_fr.get("evidence_graph")
            if isinstance(existing_fr.get("evidence_graph"), dict)
            else None
        )

        fused_graph = enrich_serialized_graph(_serialize_evidence_graph(result.graph))
        if existing_eg and (existing_eg.get("nodes") or fused_graph.get("nodes")):
            from flowsint_crypto_compliance.services.graph_merge import merge_evidence_graphs

            evidence_graph = enrich_serialized_graph(
                merge_evidence_graphs(existing_eg, fused_graph, "append")
            )
        else:
            evidence_graph = fused_graph

        try:
            neo4j_unified = project_evidence_graph(
                result.graph,
                case_ref=case.case_ref,
                investigation_id=str(case.investigation_id) if case.investigation_id else None,
            )
        except Exception:
            neo4j_unified = {"projected": 0, "case_ref": case.case_ref, "error": "projection_skipped"}

        try:
            neo4j_export = EvidenceGraphNeo4jExporter().export(
                result.graph,
                case_ref=case.case_ref,
                investigation_id=str(case.investigation_id) if case.investigation_id else None,
            )
        except Exception:
            neo4j_export = {"exported": False}

        try:
            neo4j_pivots = ComplianceNeo4jPivotExporter().export(
                result.graph,
                case_ref=case.case_ref,
            )
        except Exception:
            neo4j_pivots = {}

        hyps = list(existing_fr.get("hypotheses") or [])
        if not hyps:
            hyps = [
                {
                    "statement_ru": "Граф OSINT собран; банковские фиды отсутствуют — склейка ограниченная",
                    "confidence": 0.55,
                }
            ]

        fusion_payload = {
            "case_ref": case.case_ref,
            "attributions": [a.model_dump() for a in result.attributions],
            "bridges": [b.model_dump() for b in result.bridges],
            "linkage_scores": result.linkage_scores,
            "graph_stats": {
                "nodes": len(evidence_graph.get("nodes") or []),
                "edges": len(evidence_graph.get("edges") or []),
            },
            "evidence_graph": evidence_graph,
            "neo4j_unified": neo4j_unified,
            "neo4j_export": neo4j_export,
            "neo4j_pivots": neo4j_pivots,
            "hypotheses": hyps,
        }
        case.fusion_result = fusion_payload
        case.status = "fused"
        self.log_audit(
            case_id=case_id,
            actor_id=case.owner_id,
            action="fusion_completed",
            payload={
                "attributions": len(result.attributions),
                "bridges": len(result.bridges),
            },
        )
        self._db.commit()
        from flowsint_crypto_compliance.platform.v2.operator_events import (
            OperatorEventType,
            publish_operator_event,
        )

        publish_operator_event(
            OperatorEventType.GRAPH_UPDATED,
            payload={
                "case_id": str(case_id),
                "case_ref": case.case_ref,
                "graph_stats": fusion_payload.get("graph_stats"),
            },
            investigation_id=case.investigation_id,
            actor=str(case.owner_id),
        )
        return fusion_payload

    def fuse_case_sync(
        self,
        case_id: uuid.UUID,
        *,
        licensed_events: list[LicensedPlatformEvent] | None = None,
        control_purchases: list[ControlPurchaseEvent] | None = None,
        chain_adapters: dict | None = None,
    ) -> dict[str, Any]:
        """Synchronous wrapper for Celery workers."""
        return asyncio.run(
            self.fuse_case(
                case_id,
                licensed_events=licensed_events,
                control_purchases=control_purchases,
                chain_adapters=chain_adapters,
            )
        )

    async def fuse_case_with_report(
        self,
        case_id: uuid.UUID,
        *,
        scenario_title_ru: str = "Расследование",
        licensed_events: list[LicensedPlatformEvent] | None = None,
        control_purchases: list[ControlPurchaseEvent] | None = None,
        chain_adapters: dict | None = None,
    ) -> dict[str, Any]:
        from flowsint_crypto_compliance.reporting.regulator_report import ReportBuilder

        case = self.get_case(case_id)
        if not case:
            raise ValueError("Case not found")

        bank_rows = (
            self._db.query(ComplianceBankFeed)
            .filter(ComplianceBankFeed.case_id == case_id)
            .all()
        )
        bank_feeds = [hub_row_to_bank_feed(r.payload) for r in bank_rows]
        fiat_events = [bank_feed_to_fiat_event(b) for b in bank_feeds]

        engine = OSINTFusionEngine(
            chain_adapters=chain_adapters or {},
            label_cache=self._cache,
        )
        bundle = InvestigationBundle(
            case_id=case.case_ref,
            bank_feeds=bank_feeds,
            fiat_events=fiat_events,
            licensed_events=licensed_events or [],
            control_purchases=control_purchases or [],
        )
        result = await engine.fuse(bundle)
        report = ReportBuilder().build(
            case_ref=case.case_ref,
            scenario_title_ru=scenario_title_ru,
            fusion=result,
            bank_feed_count=len(bank_feeds),
            control_purchase_count=len(control_purchases or []),
            registry_label_count=self._cache.count(),
        )
        payload = report.to_dict()
        payload["evidence_graph"] = _serialize_evidence_graph(result.graph)
        payload["neo4j_unified"] = project_evidence_graph(
            result.graph,
            case_ref=case.case_ref,
            investigation_id=str(case.investigation_id) if case.investigation_id else None,
        )
        payload["neo4j_export"] = EvidenceGraphNeo4jExporter().export(
            result.graph,
            case_ref=case.case_ref,
            investigation_id=str(case.investigation_id) if case.investigation_id else None,
        )
        payload["neo4j_pivots"] = ComplianceNeo4jPivotExporter().export(
            result.graph,
            case_ref=case.case_ref,
        )
        payload["graph_stats"] = {
            "nodes": len(result.graph.nodes),
            "edges": len(result.graph.edges),
        }
        case.fusion_result = payload
        case.status = "reported"
        self._db.commit()
        from flowsint_crypto_compliance.platform.v2.operator_events import (
            OperatorEventType,
            publish_operator_event,
        )

        publish_operator_event(
            OperatorEventType.GRAPH_UPDATED,
            payload={
                "case_id": str(case_id),
                "case_ref": case.case_ref,
                "graph_stats": payload.get("graph_stats"),
            },
            investigation_id=case.investigation_id,
            actor=str(case.owner_id),
        )
        publish_operator_event(
            OperatorEventType.REPORT_GENERATED,
            payload={
                "case_id": str(case_id),
                "case_ref": case.case_ref,
                "format": "json",
            },
            investigation_id=case.investigation_id,
            actor=str(case.owner_id),
        )
        return payload

    def list_cases(
        self,
        owner_id: uuid.UUID | None = None,
        *,
        workflow_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ComplianceCase]:
        q = self._db.query(ComplianceCase).order_by(
            ComplianceCase.queue_priority.asc().nullslast(),
            ComplianceCase.updated_at.desc(),
        )
        if owner_id:
            q = q.filter(
                (ComplianceCase.owner_id == owner_id) | (ComplianceCase.assignee_id == owner_id)
            )
        if workflow_status:
            q = q.filter(ComplianceCase.workflow_status == workflow_status)
        return q.offset(offset).limit(min(limit, 200)).all()

    def transition_case(
        self,
        case_id: uuid.UUID,
        *,
        workflow_status: str,
        actor_id: uuid.UUID,
        assignee_id: uuid.UUID | None = None,
        priority: str | None = None,
        queue_priority: int | None = None,
    ) -> ComplianceCase:
        from flowsint_crypto_compliance.services.case_workflow import (
            can_transition,
            is_sla_breached,
            sla_due_at,
        )
        from flowsint_crypto_compliance.observability.metrics import COMPLIANCE_SLA_BREACH_TOTAL

        case = self.get_case(case_id)
        if not case:
            raise ValueError("Case not found")
        current = case.workflow_status or "new"
        if not can_transition(current, workflow_status):
            raise ValueError(f"Invalid transition {current} → {workflow_status}")
        case.workflow_status = workflow_status
        if assignee_id is not None:
            case.assignee_id = assignee_id
        if priority:
            case.priority = priority
        if queue_priority is not None:
            case.queue_priority = queue_priority
        case.due_at = sla_due_at(workflow_status)
        case.sla_breached = is_sla_breached(case.due_at, workflow_status)
        if case.sla_breached:
            COMPLIANCE_SLA_BREACH_TOTAL.inc()
        status_map = {
            "new": "draft",
            "triage": "ingesting",
            "investigating": "fused",
            "pending_filing": "fused",
            "filed": "reported",
            "archived": "reported",
        }
        case.status = status_map.get(workflow_status, case.status)
        self.log_audit(
            case_id=case_id,
            actor_id=actor_id,
            action="case_status_changed",
            payload={"from": current, "to": workflow_status, "assignee_id": str(assignee_id) if assignee_id else None},
        )
        self._db.commit()
        self._db.refresh(case)
        return case

    def add_comment(self, case_id: uuid.UUID, author_id: uuid.UUID, body: str) -> ComplianceCaseComment:
        comment = ComplianceCaseComment(case_id=case_id, author_id=author_id, body=body.strip())
        self._db.add(comment)
        self.log_audit(case_id=case_id, actor_id=author_id, action="case_comment_added", payload={"length": len(body)})
        self._db.commit()
        self._db.refresh(comment)
        return comment

    def list_comments(self, case_id: uuid.UUID) -> list[ComplianceCaseComment]:
        return (
            self._db.query(ComplianceCaseComment)
            .filter(ComplianceCaseComment.case_id == case_id)
            .order_by(ComplianceCaseComment.created_at.asc())
            .all()
        )

    def load_profiles(self, user_ids: set[uuid.UUID]) -> dict[uuid.UUID, Any]:
        if not user_ids:
            return {}
        from flowsint_core.core.models import Profile

        rows = self._db.query(Profile).filter(Profile.id.in_(user_ids)).all()
        return {row.id: row for row in rows}

    def get_case_risk_history(self, case_id: uuid.UUID) -> list[dict[str, Any]]:
        """Risk score time-series from audit log and stored fusion reports."""
        from flowsint_crypto_compliance.services.graph_timestamps import _normalize_timestamp

        points: list[dict[str, Any]] = []
        seen: set[tuple[str, float]] = set()

        def _add(ts_raw: Any, score: float, source: str) -> None:
            ts = _normalize_timestamp(ts_raw)
            if not ts or score is None:
                return
            key = (ts, round(float(score), 2))
            if key in seen:
                return
            seen.add(key)
            points.append({"ts": ts, "score": round(float(score), 2), "source": source})

        for row in reversed(self.list_audit_log(case_id=case_id, limit=200)):
            payload = row.payload or {}
            score: float | None = None
            if row.action == "wallet_screened" and payload.get("risk_score") is not None:
                score = float(payload["risk_score"])
            elif row.action in ("risk_score_changed", "risk_recalculated") and (
                payload.get("score") is not None or payload.get("risk_score") is not None
            ):
                score = float(payload.get("score") if payload.get("score") is not None else payload["risk_score"])
            if score is not None:
                _add(row.created_at, score, row.action)

        case = self.get_case(case_id)
        if case and case.fusion_result:
            fusion = case.fusion_result
            fz = fusion.get("fz115_report") if isinstance(fusion.get("fz115_report"), dict) else fusion
            if isinstance(fz, dict):
                for key in ("illegal_flow_score", "risk_score"):
                    if fz.get(key) is not None:
                        _add(
                            fz.get("generated_at") or case.updated_at,
                            float(fz[key]),
                            "fz115_report",
                        )
                        break
            report = fusion.get("forensic_report") if isinstance(fusion.get("forensic_report"), dict) else None
            if report and report.get("risk_score") is not None:
                _add(case.updated_at, float(report["risk_score"]), "forensic_report")

        points.sort(key=lambda p: p["ts"])
        return points

    def risk_trend_indicator(self, history: list[dict[str, Any]]) -> str | None:
        if len(history) < 2:
            return None
        prev = float(history[-2]["score"])
        curr = float(history[-1]["score"])
        delta = curr - prev
        if delta >= 5:
            return "↑"
        if delta <= -5:
            return "↓"
        return "→"

    def get_cross_case_graph_links(self, case_ref: str, *, limit: int = 20) -> list[dict[str, Any]]:
        case = self.get_case_by_ref(case_ref)
        if not case:
            return []

        entity_keys: set[str] = set()
        fusion = case.fusion_result or {}
        graph = fusion.get("evidence_graph") if isinstance(fusion.get("evidence_graph"), dict) else {}
        for node in graph.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            label = str(node.get("label") or node.get("id") or "").strip()
            if not label:
                continue
            if ":" in label:
                entity_keys.add(label.split(":", 1)[-1].lower())
            elif len(label) >= 8:
                entity_keys.add(label.lower())

        findings = self._db.query(OsintFinding).filter(OsintFinding.case_id == case.id).all()
        for finding in findings:
            entity_keys.add(str(finding.entity_value).lower())

        if not entity_keys:
            return []

        keys = list(entity_keys)[:50]
        rows = (
            self._db.query(OsintFinding, ComplianceCase)
            .join(ComplianceCase, ComplianceCase.id == OsintFinding.case_id)
            .filter(
                OsintFinding.case_id != case.id,
                OsintFinding.entity_value.in_(keys),
            )
            .order_by(ComplianceCase.updated_at.desc())
            .limit(limit)
            .all()
        )

        links: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for finding, other_case in rows:
            dedupe = (other_case.case_ref, finding.entity_value)
            if dedupe in seen:
                continue
            seen.add(dedupe)
            links.append(
                {
                    "case_ref": other_case.case_ref,
                    "case_id": str(other_case.id),
                    "entity_type": finding.entity_type,
                    "entity_value": finding.entity_value,
                    "relation": "shared_entity",
                    "confidence": finding.confidence,
                }
            )
        return links

    def reorder_case_queue(self, ordered_case_ids: list[uuid.UUID], *, actor_id: uuid.UUID) -> int:
        updated = 0
        for index, case_id in enumerate(ordered_case_ids):
            case = self.get_case(case_id)
            if not case:
                continue
            case.queue_priority = index
            updated += 1
        if updated:
            self.log_audit(
                actor_id=actor_id,
                action="queue_reordered",
                payload={"ordered_count": updated, "case_ids": [str(cid) for cid in ordered_case_ids[:50]]},
            )
            self._db.commit()
        return updated

    def workflow_stats(self, owner_id: uuid.UUID | None = None) -> dict[str, Any]:
        from flowsint_crypto_compliance.services.case_workflow import WORKFLOW_STATUSES

        cases = self.list_cases(owner_id, limit=500)
        pipeline = {s: 0 for s in WORKFLOW_STATUSES}
        for case in cases:
            ws = case.workflow_status or "new"
            if ws in pipeline:
                pipeline[ws] += 1
        pipeline["filed_mtd"] = pipeline.get("filed", 0)
        return {
            "pipeline": pipeline,
            "total": len(cases),
            "sla_breached": sum(1 for c in cases if c.sla_breached),
        }

    def merge_case_graph(
        self,
        case_id: uuid.UUID,
        evidence_graph: dict[str, Any],
        *,
        merge_mode: str = "append",
        actor_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        from flowsint_crypto_compliance.services.graph_merge import merge_evidence_graphs
        from flowsint_crypto_compliance.services.graph_timestamps import enrich_serialized_graph

        case = self.get_case(case_id)
        if not case:
            raise ValueError("Case not found")

        fusion = dict(case.fusion_result or {})
        current = fusion.get("evidence_graph") if isinstance(fusion.get("evidence_graph"), dict) else None
        merged = merge_evidence_graphs(current, evidence_graph, merge_mode)
        merged = enrich_serialized_graph(merged)
        stats = {"nodes": len(merged.get("nodes") or []), "edges": len(merged.get("edges") or [])}

        fusion["evidence_graph"] = merged
        fusion["graph_stats"] = stats
        fusion.setdefault("case_ref", case.case_ref)
        case.fusion_result = fusion
        self._db.commit()
        self._db.refresh(case)

        if actor_id:
            self.log_audit(
                actor_id=actor_id,
                action="graph_merged",
                payload={
                    "case_id": str(case_id),
                    "case_ref": case.case_ref,
                    "merge_mode": merge_mode,
                    "graph_stats": stats,
                },
            )
            self._db.commit()

        return {
            "ok": True,
            "case_ref": case.case_ref,
            "graph_stats": stats,
            "evidence_graph": merged,
        }


def _serialize_evidence_graph(graph) -> dict[str, Any]:
    """Prefer Scalpel bridge serializer so attribution/sanctions flags survive merge."""
    try:
        from flowsint_crypto_compliance.osint_core.scalpel.evidence_bridge import (
            serialize_evidence_graph as _scalpel_serialize,
        )

        payload = _scalpel_serialize(graph)
        from flowsint_crypto_compliance.services.graph_timestamps import (
            _normalize_timestamp,
            _payload_timestamp,
        )

        for node_row, node in zip(payload.get("nodes") or [], graph.nodes):
            ts = _payload_timestamp(node.payload or {})
            if ts:
                node_row["timestamp"] = ts
                node_row["occurred_at"] = ts
        for edge_row, edge in zip(payload.get("edges") or [], graph.edges):
            for hint in edge.evidence or []:
                ts = _normalize_timestamp(hint) if isinstance(hint, str) and "T" in hint else None
                if ts:
                    edge_row["timestamp"] = ts
                    edge_row["occurred_at"] = ts
                    break
        return payload
    except Exception:
        from flowsint_crypto_compliance.services.graph_timestamps import (
            _normalize_timestamp,
            _payload_timestamp,
        )

        nodes: list[dict[str, Any]] = []
        for node in graph.nodes:
            node_payload = node.payload or {}
            ts = _payload_timestamp(node_payload)
            node_row: dict[str, Any] = {
                "id": node.node_id,
                "kind": node.kind.value,
                "label": node_payload.get("display_label") or node.primary_key,
                "region": node.region,
                "confidence": node.confidence,
            }
            for key in (
                "address",
                "attribution",
                "owner",
                "owner_category",
                "sanctioned",
                "scam",
                "flags",
                "risk_tags",
            ):
                if key in node_payload:
                    node_row[key] = node_payload[key]
            if ts:
                node_row["timestamp"] = ts
                node_row["occurred_at"] = ts
            nodes.append(node_row)

        edges: list[dict[str, Any]] = []
        for edge in graph.edges:
            edge_row: dict[str, Any] = {
                "id": edge.edge_id,
                "source": edge.from_id,
                "target": edge.to_id,
                "rel_type": edge.rel_type,
                "strength": edge.strength,
            }
            for hint in edge.evidence or []:
                ts = _normalize_timestamp(hint) if isinstance(hint, str) and "T" in hint else None
                if ts:
                    edge_row["timestamp"] = ts
                    edge_row["occurred_at"] = ts
                    break
            edges.append(edge_row)

        return {"nodes": nodes, "edges": edges}
