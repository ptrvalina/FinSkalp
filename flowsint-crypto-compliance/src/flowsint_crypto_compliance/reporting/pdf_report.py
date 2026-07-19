"""HTML/PDF export for 115-ФЗ reports (Jinja2 templates; WeasyPrint optional)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATES = Path(__file__).resolve().parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES)),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_fz115_html(report: dict[str, Any]) -> str:
    template = _env.get_template("fz115.html.j2")
    return template.render(report=report)


def render_regulator_html(report: dict[str, Any]) -> str:
    metrics = report.get("metrics") or {}
    risk_scoring = metrics.get("risk_scoring") or {}
    template = _env.get_template("regulator.html.j2")
    return template.render(
        report=_normalize_regulator_payload(report),
        metrics=metrics,
        risk_scoring=risk_scoring,
        xgb=risk_scoring.get("xgboost"),
    )


def _normalize_regulator_payload(report: dict[str, Any]) -> dict[str, Any]:
    """Flatten nested investigate / fusion payloads for the regulator template."""
    out = dict(report)
    screening = report.get("screening") if isinstance(report.get("screening"), dict) else {}
    forensic = report.get("forensic_report") if isinstance(report.get("forensic_report"), dict) else {}
    address_report = report.get("address_report") if isinstance(report.get("address_report"), dict) else {}
    open_osint = report.get("open_osint") if isinstance(report.get("open_osint"), dict) else {}

    if out.get("illegal_flow_score") is None:
        out["illegal_flow_score"] = (
            screening.get("risk_score")
            or report.get("risk_score")
            or report.get("composite_risk")
        )
    if not out.get("risk_level"):
        out["risk_level"] = screening.get("risk_level") or report.get("risk_level")

    if not out.get("executive_summary_ru"):
        exec_block = forensic.get("executive_summary") or address_report.get("executive_summary")
        if isinstance(exec_block, dict):
            out["executive_summary_ru"] = exec_block.get("text_ru") or exec_block.get("summary_ru")
        out["executive_summary_ru"] = (
            out.get("executive_summary_ru")
            or report.get("summary_ru")
            or open_osint.get("summary_ru")
        )

    if not out.get("findings"):
        findings = list(screening.get("findings") or [])
        for mention in (open_osint.get("mentions") or [])[:12]:
            if not isinstance(mention, dict):
                continue
            findings.append(
                {
                    "severity": mention.get("risk_tag") or "osint",
                    "title_ru": mention.get("title_ru") or mention.get("source_name") or "OSINT hit",
                }
            )
        out["findings"] = findings

    if not out.get("decision_ru"):
        decision = forensic.get("decision") or address_report.get("decision")
        if isinstance(decision, dict):
            out["decision_ru"] = decision.get("text_ru") or decision.get("recommendation_ru")
        elif isinstance(decision, str):
            out["decision_ru"] = decision

    if out.get("attributions") is None and report.get("attributions"):
        out["attributions"] = report.get("attributions")

    return out


def _prepare_weasyprint_runtime() -> None:
    """Expose GTK/Pango DLLs for WeasyPrint on Windows."""
    if os.name != "nt":
        return
    candidates = [
        Path(r"C:\Program Files\GTK3-Runtime Win64\bin"),
        Path(r"C:\Program Files\Gtk-Runtime\bin"),
    ]
    for dll_dir in candidates:
        if not dll_dir.is_dir():
            continue
        current_path = os.environ.get("PATH", "")
        if str(dll_dir) not in current_path:
            os.environ["PATH"] = f"{dll_dir}{os.pathsep}{current_path}"
        add_dll_directory = getattr(os, "add_dll_directory", None)
        if add_dll_directory is not None:
            try:
                add_dll_directory(str(dll_dir))
            except OSError:
                pass
        break


def render_pdf_bytes(html: str) -> tuple[bytes, str]:
    """
    Return (content, media_type).
    Falls back to HTML when WeasyPrint is unavailable.
    """
    try:
        _prepare_weasyprint_runtime()
        from weasyprint import HTML

        return HTML(string=html).write_pdf(), "application/pdf"
    except Exception:
        return html.encode("utf-8"), "text/html; charset=utf-8"
