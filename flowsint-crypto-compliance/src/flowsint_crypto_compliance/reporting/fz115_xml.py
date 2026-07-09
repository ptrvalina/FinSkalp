"""
115-FZ XML export — methodological XML for Rosfinmonitoring filing pipeline.

Based on open 115-FZ structure (operation message / STR). Validate against
your bank's актуальный XSD from ФЭС Росфинмониторинга before production filing.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any
from xml.dom import minidom


NS = "http://finskalp.local/fz115/v1"


def _el(parent: ET.Element, tag: str, text: str | None = None, **attrs: str) -> ET.Element:
    node = ET.SubElement(parent, tag, attrs)
    if text is not None:
        node.text = str(text)
    return node


def fz115_report_to_xml(report: dict[str, Any], *, locale: str = "ru") -> str:
    root = ET.Element("SuspiciousOperationReport", xmlns=NS, version="1.0", locale=locale)
    _el(root, "ReportId", report.get("report_id", ""))
    _el(root, "GeneratedAt", report.get("generated_at", ""))
    _el(root, "CaseRef", report.get("case_ref", ""))
    _el(root, "AlertCode", report.get("alert_code", ""))

    meta = ET.SubElement(root, "Metadata")
    _el(meta, "ReportType", _localized(report, "report_type", locale))
    _el(meta, "Classification", _localized(report, "classification", locale))
    _el(meta, "RiskLevel", report.get("risk_level", "medium"))
    _el(meta, "IllegalFlowScore", str(report.get("illegal_flow_score", 0)))

    legal = ET.SubElement(root, "LegalBasis")
    for item in report.get("legal_basis_ru") or []:
        _el(legal, "Basis", item)

    subject = ET.SubElement(root, "Subject")
    _el(subject, "Category", _localized(report, "subject_category", locale))
    _el(subject, "TypologyCode", report.get("typology_code", ""))
    _el(subject, "TypologyName", _localized(report, "typology_name", locale))
    if report.get("bank_name"):
        _el(subject, "BankName", report["bank_name"])
    if report.get("operation_amount"):
        _el(subject, "OperationAmount", report["operation_amount"])

    signs = ET.SubElement(root, "SuspicionSigns")
    for sign in report.get("suspicion_signs") or []:
        s = ET.SubElement(signs, "Sign")
        _el(s, "Description", sign.get("article_ru") or sign.get("description", ""))
        _el(s, "Confirmed", sign.get("confirmed", "да"))

    evidence = ET.SubElement(root, "Evidence")
    for item in report.get("evidence_items") or []:
        _el(evidence, "Item", item)

    decision = ET.SubElement(root, "Decision")
    _el(decision, "Text", _localized(report, "decision", locale))
    _el(decision, "Basis", _localized(report, "decision_basis", locale))
    actions = ET.SubElement(decision, "RecommendedActions")
    for act in _localized_list(report, "recommended_actions", locale):
        _el(actions, "Action", act)

    _el(root, "ExecutiveSummary", _localized(report, "executive_summary", locale))
    _el(root, "ResponsibleOfficer", _localized(report, "responsible_officer", locale))

    rough = ET.tostring(root, encoding="unicode")
    return minidom.parseString(rough).toprettyxml(indent="  ")


def _localized(report: dict[str, Any], field: str, locale: str) -> str:
    if locale == "en":
        return str(report.get(f"{field}_en") or report.get(f"{field}_ru") or report.get(field, ""))
    return str(report.get(f"{field}_ru") or report.get(field, ""))


def _localized_list(report: dict[str, Any], field: str, locale: str) -> list[str]:
    if locale == "en":
        return list(report.get(f"{field}_en") or report.get(f"{field}_ru") or report.get(field) or [])
    return list(report.get(f"{field}_ru") or report.get(field) or [])
