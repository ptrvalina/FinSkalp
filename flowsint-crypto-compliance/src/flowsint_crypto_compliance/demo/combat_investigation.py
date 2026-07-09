"""Case investigation pipeline — live FinSkalp (on-chain + multi-hop graph)."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from flowsint_crypto_compliance.demo.combat_mode import is_combat_mode, resolve_alert_crypto
from flowsint_crypto_compliance.demo.graph_viz_adapter import (
    ensure_investigation_graph,
    evidence_graph_to_viz,
)
from flowsint_crypto_compliance.demo.live_ops_metrics import get_live_ops_metrics
from flowsint_crypto_compliance.services.finskalp_investigator import (
    FinSkalpInvestigationRequest,
    FinSkalpInvestigator,
)
from flowsint_types.fiat_crypto import Chain

OnStep = Callable[[list[dict[str, Any]]], Awaitable[None] | None]


class CombatInvestigationPipeline:
    """Full investigation for ops inbox — same engine as FinSkalp OSINT center."""

    def __init__(self) -> None:
        self._finskalp = FinSkalpInvestigator()

    async def run_for_alert(
        self,
        alert: dict[str, Any],
        *,
        on_step: OnStep | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        address, chain = resolve_alert_crypto(alert)
        case_ref = alert.get("case_ref") or f"OPS-{alert.get('alert_code', 'CASE')}"

        async def on_phase(phases: list[dict[str, Any]]) -> None:
            steps = [
                {
                    "id": p.get("id", f"step-{i}"),
                    "label_ru": p.get("label_ru", ""),
                    "detail_ru": p.get("detail_ru", ""),
                    "status": p.get("status", "done"),
                }
                for i, p in enumerate(phases)
            ]
            if on_step:
                await on_step(steps)

        req = FinSkalpInvestigationRequest(
            address=address,
            chain=chain,
            bank_reference=alert.get("hub_feed_id"),
            bank_name=alert.get("bank_name"),
            amount=alert.get("amount"),
            currency=alert.get("currency") or "RUB",
            region=alert.get("region") or "RU",
            notes=alert.get("summary_ru"),
            scenario_id=None if is_combat_mode() else alert.get("scenario_id"),
            depth=2,
            osint_depth=2,
            limit=300,
        )

        result = await self._finskalp.investigate(req, on_phase=on_phase)
        report = dict(result.fusion_report)
        report["scenario_title_ru"] = alert.get("official_title_ru") or alert.get("title_ru") or case_ref
        report["case_ref"] = case_ref
        report["investigation_id"] = result.investigation_id
        report["live_fusion"] = result.live_fusion
        report["screening"] = result.screening
        report["address"] = result.address
        report["chain"] = result.chain.value

        evidence_viz = None
        if self._finskalp._last_fusion is not None:
            from flowsint_crypto_compliance.detection.findings import IllegalFlowFinding

            parsed = [
                IllegalFlowFinding(
                    severity=f.get("severity", "medium"),
                    code=f.get("code", ""),
                    title_ru=f.get("title_ru", ""),
                    description_ru=f.get("description_ru", ""),
                    addresses=f.get("addresses") or [],
                    evidence=f.get("evidence"),
                    confidence=f.get("confidence", 0.5),
                )
                for f in (report.get("findings") or [])
            ]
            evidence_viz = evidence_graph_to_viz(self._finskalp._last_fusion.graph, parsed)

        graph_viz = ensure_investigation_graph(
            address=result.address,
            chain=result.chain.value,
            live_fusion=result.live_fusion,
            onchain=(result.screening or {}).get("onchain_summary"),
            evidence_graph_viz=evidence_viz,
        )
        report["graph_viz"] = graph_viz or {}
        report["live_fusion"] = graph_viz if graph_viz.get("nodes") else result.live_fusion
        report["forensic_report"] = getattr(result, "forensic_report", None) or {}
        report["screening"] = result.screening
        report["address_report"] = result.address_report
        report["volumetric_report"] = result.volumetric_report
        report["sar_report"] = result.sar_report
        report["seizure_report"] = result.seizure_report
        report["attachments"] = result.attachments
        report["_finskalp_cache"] = result.to_dict()

        nodes = int(graph_viz.get("node_count") or len(graph_viz.get("nodes") or []))
        edges = int(graph_viz.get("edge_count") or len(graph_viz.get("edges") or []))
        get_live_ops_metrics().record_investigation(
            duration_ms=result.duration_ms,
            graph_nodes=nodes,
            graph_edges=edges,
        )

        steps = [
            {
                "id": p.get("id", ""),
                "label_ru": p.get("label_ru", ""),
                "detail_ru": p.get("detail_ru", ""),
                "status": p.get("status", "done"),
            }
            for p in result.phases
        ]
        return steps, report
