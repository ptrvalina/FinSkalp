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
        report=report,
        metrics=metrics,
        risk_scoring=risk_scoring,
        xgb=risk_scoring.get("xgboost"),
    )


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
