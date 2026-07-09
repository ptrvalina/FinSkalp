"""
Объёмные отчёты FinSkalp — без усечения findings/mentions для материалов ФИУ.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.osint_core.fusion_engine import FusionResult


class VolumetricReportBuilder:
    """Полный пакет доказательств для Росфинмониторинга / суда."""

    def build(
        self,
        *,
        investigation_id: str,
        case_ref: str,
        address: str,
        chain: str,
        screening: dict[str, Any],
        fusion_report: dict[str, Any],
        fusion: FusionResult | None = None,
        open_osint: dict[str, Any] | None = None,
        ocr_documents: list[dict[str, Any]] | None = None,
        forensic_report: dict[str, Any] | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        findings = list(screening.get("findings") or [])
        fusion_findings = fusion_report.get("findings") or []
        mentions = (open_osint or {}).get("mentions") or []
        rejected = (open_osint or {}).get("rejected_junk_sample") or []

        graph_nodes = fusion_report.get("evidence_graph", {}).get("nodes", 0)
        graph_edges = fusion_report.get("evidence_graph", {}).get("edges", 0)

        sections = _build_sections(
            findings=findings,
            fusion_findings=fusion_findings,
            mentions=mentions,
            attributions=fusion.attributions if fusion else [],
            corridors=fusion.corridor_matches if fusion else [],
        )

        return {
            "report_type": "volumetric",
            "product": "FinSkalp",
            "product_ru": "ФинСкальп",
            "title_ru": "Объёмный отчёт расследования · полный пакет доказательств",
            "classification": "КОНФИДЕНЦИАЛЬНО · 115-ФЗ",
            "report_id": investigation_id,
            "case_ref": case_ref,
            "generated_at": _now(),
            "volume_stats": {
                "findings_total": len(findings) + len(fusion_findings),
                "mentions_total": len(mentions),
                "junk_rejected": len(rejected),
                "ocr_documents": len(ocr_documents or []),
                "graph_nodes": graph_nodes,
                "graph_edges": graph_edges,
                "sections_count": len(sections),
                "pages_estimate": max(1, (len(findings) + len(mentions)) // 8 + 12),
            },
            "address": address,
            "chain": chain,
            "executive_summary_ru": (forensic_report or {}).get("executive_summary", {}).get(
                "text_ru", ""
            ),
            "sections": sections,
            "all_findings": findings,
            "all_fusion_findings": fusion_findings,
            "all_mentions": mentions,
            "rejected_junk": rejected,
            "open_osint": open_osint or {},
            "ocr_documents": ocr_documents or [],
            "fusion_report": fusion_report,
            "screening": screening,
            "methodology_ru": [
                "FinSkalp Scalpel OSINT — параллельные коллекторы (clearnet, Tor, paste, username)",
                "Отсев мусора — reputation + confidence + spam filters",
                "Суверенный fusion-граф банк↔крипто",
                "OCR изъятия — PyMuPDF/Tesseract → сущности → кошельки",
            ],
            "notes": notes,
        }


def _build_sections(
    *,
    findings: list[dict[str, Any]],
    fusion_findings: list[dict[str, Any]],
    mentions: list[dict[str, Any]],
    attributions: list[Any],
    corridors: list[dict[str, object]],
) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []

    sections.append({
        "id": "screening",
        "title_ru": "Скрининг и реестр 115-ФЗ",
        "items": findings,
        "count": len(findings),
    })
    sections.append({
        "id": "fusion_aml",
        "title_ru": "AML / детектор нелегальных потоков",
        "items": fusion_findings,
        "count": len(fusion_findings),
    })
    sections.append({
        "id": "open_osint",
        "title_ru": "Открытый OSINT · Scalpel",
        "items": mentions,
        "count": len(mentions),
    })
    sections.append({
        "id": "attribution",
        "title_ru": "Суверенная атрибуция",
        "items": [_serialize_attribution(a) for a in attributions],
        "count": len(attributions),
    })
    sections.append({
        "id": "corridors",
        "title_ru": "Коридоры и транзит",
        "items": list(corridors),
        "count": len(corridors),
    })
    return sections


def _entity_kind_value(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    return str(getattr(raw, "value", raw))


def _serialize_attribution(a: Any) -> dict[str, Any]:
    """Map FusedAttribution (or dict fallback) to volumetric section row."""
    if isinstance(a, dict):
        black = bool(a.get("black_zone"))
        gray = bool(a.get("gray_zone"))
        return {
            "wallet": a.get("address") or a.get("wallet_address") or a.get("wallet") or "",
            "entity": (
                a.get("sovereign_label")
                or a.get("watchlist_label")
                or a.get("entity_name")
                or _entity_kind_value(a.get("entity_kind"))
            ),
            "primary_region": a.get("primary_region"),
            "confidence": a.get("confidence", 0),
            "zone": "black" if black else ("gray" if gray else "clear"),
            "black_zone": black,
            "gray_zone": gray,
            "label_source": a.get("label_source"),
            "sanctioned": bool(a.get("sanctioned")),
        }

    black = bool(getattr(a, "black_zone", False))
    gray = bool(getattr(a, "gray_zone", False))
    return {
        "wallet": getattr(a, "address", "") or getattr(a, "wallet_address", ""),
        "entity": (
            getattr(a, "sovereign_label", None)
            or getattr(a, "watchlist_label", None)
            or _entity_kind_value(getattr(a, "entity_kind", None))
        ),
        "primary_region": getattr(a, "primary_region", None),
        "confidence": getattr(a, "confidence", 0),
        "zone": "black" if black else ("gray" if gray else "clear"),
        "black_zone": black,
        "gray_zone": gray,
        "label_source": getattr(a, "label_source", None),
        "sanctioned": bool(getattr(a, "sanctioned", False)),
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
