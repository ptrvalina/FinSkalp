"""
Отчёт для изъятия незаконных активов (115-ФЗ / УПК РФ материалы).

OCR-документы + on-chain + OSINT Scalpel → пакет для правоохранительных органов.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class SeizureReportBuilder:
    def build(
        self,
        *,
        investigation_id: str,
        case_ref: str,
        address: str,
        chain: str,
        screening: dict[str, Any],
        fusion_report: dict[str, Any],
        open_osint: dict[str, Any] | None = None,
        ocr_documents: list[dict[str, Any]] | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        ocr_docs = ocr_documents or []
        wallets_from_ocr = []
        for doc in ocr_docs:
            for w in (doc.get("seizure_fields") or {}).get("wallets") or []:
                wallets_from_ocr.append(w)
            for w in (doc.get("entities") or {}).get("crypto_addresses") or []:
                wallets_from_ocr.append(w)

        all_wallets = _uniq_wallets(
            [{"address": address, "chain": chain, "role": "primary"}]
            + [{"address": w.get("address"), "chain": w.get("chain", chain), "role": "ocr_extracted"} for w in wallets_from_ocr]
            + [{"address": a.get("address"), "chain": a.get("chain", chain), "role": "osint_linked"}
               for a in (open_osint or {}).get("extracted_entities", {}).get("aggregate", {}).get("crypto_addresses", [])]
        )

        return {
            "report_type": "seizure",
            "product": "FinSkalp",
            "product_ru": "ФинСкальп",
            "title_ru": "Материалы для изъятия цифровых активов",
            "subtitle_ru": "115-ФЗ · ПОД/ФТ · блокировка/конфискация криптоактивов",
            "classification": "КОНФИДЕНЦИАЛЬНО · ДСП",
            "report_id": investigation_id,
            "case_ref": case_ref,
            "generated_at": _now(),
            "legal_basis_ru": [
                "Федеральный закон № 115-ФЗ «О противодействии легализации доходов»",
                "Ст. 76 УПК РФ — изъятие вещей и документов",
                "Постановления Пленума ВС РФ по обеспечительным мерам на цифровые активы",
            ],
            "subject": {
                "primary_wallet": address,
                "chain": chain.upper(),
                "risk_score": screening.get("risk_score"),
                "risk_level": screening.get("risk_level"),
                "illegal_flow_score": fusion_report.get("illegal_flow_score"),
            },
            "assets_for_seizure": {
                "wallets": all_wallets,
                "estimated_exposure_rub": _estimate_exposure(screening, fusion_report),
                "corridors": fusion_report.get("corridors") or [],
                "bridges": fusion_report.get("bridges") or [],
            },
            "ocr_evidence": {
                "documents_count": len(ocr_docs),
                "documents": [
                    {
                        "filename": d.get("filename"),
                        "backend": d.get("backend"),
                        "confidence": d.get("confidence"),
                        "seizure_fields": d.get("seizure_fields"),
                        "preview": (d.get("full_text_preview") or "")[:800],
                    }
                    for d in ocr_docs
                ],
            },
            "osint_evidence": {
                "mentions_count": (open_osint or {}).get("mentions_count", 0),
                "independent_sources": (open_osint or {}).get("independent_sources", 0),
                "extracted_entities": (open_osint or {}).get("extracted_entities"),
                "top_mentions": ((open_osint or {}).get("mentions") or [])[:30],
            },
            "findings": (screening.get("findings") or []) + (fusion_report.get("findings") or []),
            "recommended_actions_ru": [
                "Направить запрос в VASP/банк о блокировке кошелька и связанных счетов",
                "Зафиксировать on-chain снимок (block height) для последующей конфискации",
                "Приложить OCR-материалы и OSINT-цепочку доказательств к постановлению",
                "Уведомить Росфинмониторинг при признаках ст. 6 115-ФЗ",
            ],
            "evidence_chain": screening.get("evidence_chain") or [],
            "notes": notes,
        }


def _uniq_wallets(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for w in items:
        addr = (w.get("address") or "").strip()
        if not addr or addr in seen:
            continue
        seen.add(addr)
        out.append(w)
    return out


def _estimate_exposure(screening: dict[str, Any], fusion: dict[str, Any]) -> str | None:
    onchain = screening.get("onchain_summary") or {}
    inbound = onchain.get("inbound_volume_usd") or onchain.get("inbound_count")
    if inbound:
        return f"on-chain activity indicator: {inbound}"
    score = fusion.get("illegal_flow_score")
    if score and score > 70:
        return "высокий индекс нелегального потока — требуется углублённая оценка"
    return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
