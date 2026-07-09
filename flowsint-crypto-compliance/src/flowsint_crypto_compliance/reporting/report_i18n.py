"""Bilingual report fields (RU / EN) for regulator and partner banks."""

from __future__ import annotations

from typing import Any

_EN_MAP = {
    "report_type_ru": "Suspicious operation verification report (115-FZ)",
    "classification_ru": "Confidential — internal use",
    "subject_category_ru": "Virtual asset service user / crypto counterparty",
    "decision_ru": "Refer enhanced due diligence materials to the financial intelligence unit",
    "decision_basis_ru": "Suspicion indicators confirmed by on-chain and registry evidence.",
    "responsible_officer_ru": "Senior AML/CFT Analyst — Digital Assets Desk",
    "executive_summary_ru": "Investigation completed under 115-FZ framework with documented evidence chain.",
}


def localize_fz115_report(report: dict[str, Any], locale: str = "ru") -> dict[str, Any]:
    out = dict(report)
    if locale == "en":
        for ru_key, en_val in _EN_MAP.items():
            en_key = ru_key.replace("_ru", "_en")
            out[en_key] = en_val if ru_key in report else out.get(en_key, en_val)
        if report.get("findings_summary_ru"):
            out["findings_summary_en"] = [
                f.replace("КРИТИЧ.", "CRITICAL").replace("ВЫСОК.", "HIGH")
                for f in report["findings_summary_ru"]
            ]
        if report.get("recommended_actions_ru"):
            out["recommended_actions_en"] = [
                a.replace("Росфинмониторинг", "FIU")
                .replace("115-ФЗ", "115-FZ")
                for a in report["recommended_actions_ru"]
            ]
        if report.get("legal_basis_ru"):
            out["legal_basis_en"] = [
                "Federal Law No. 115-FZ on AML/CFT (Russia)",
                "Article 6 — suspicious operation indicators",
                "Article 7 — reporting obligations",
            ]
    out["locale"] = locale
    return out
