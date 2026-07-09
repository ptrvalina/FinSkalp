"""Direction 3 & 4 unit tests — workflow, XML, batch parse, degradation."""

from __future__ import annotations

import hashlib
import hmac

from flowsint_crypto_compliance.infrastructure.circuit_breaker import CollectorCircuitBreaker
from flowsint_crypto_compliance.reporting.fz115_xml import fz115_report_to_xml
from flowsint_crypto_compliance.reporting.report_i18n import localize_fz115_report
from flowsint_crypto_compliance.services.batch_parser import parse_address_rows
from flowsint_crypto_compliance.services.case_workflow import can_transition, is_sla_breached, sla_due_at


def test_workflow_transitions():
    assert can_transition("new", "triage")
    assert not can_transition("filed", "new")
    assert can_transition("pending_filing", "filed")


def test_sla_due_at_future():
    due = sla_due_at("investigating")
    assert due is not None
    assert not is_sla_breached(due, "investigating")


def test_parse_csv_addresses():
    raw = b"address,chain\nTAddr123,tron\n0xabc,eth\n"
    rows = parse_address_rows(raw, filename="wallets.csv")
    assert len(rows) == 2
    assert rows[0]["chain"] == "tron"


def test_fz115_xml_contains_report_id():
    report = {
        "report_id": "OT-1",
        "generated_at": "2026-07-01T00:00:00Z",
        "case_ref": "CASE-1",
        "alert_code": "AL-1",
        "report_type_ru": "Справка",
        "classification_ru": "ДСП",
        "legal_basis_ru": ["115-ФЗ"],
        "subject_category_ru": "Субъект",
        "typology_code": "P2P",
        "typology_name_ru": "P2P",
        "suspicion_signs": [{"article_ru": "ст.6", "confirmed": "да"}],
        "evidence_items": ["graph"],
        "decision_ru": "Направить",
        "decision_basis_ru": "Основание",
        "recommended_actions_ru": ["Действие"],
        "executive_summary_ru": "Итог",
        "responsible_officer_ru": "Аналитик",
        "risk_level": "high",
        "illegal_flow_score": 77,
    }
    xml = fz115_report_to_xml(report, locale="ru")
    assert "OT-1" in xml
    assert "SuspiciousOperationReport" in xml


def test_localize_en():
    report = {"decision_ru": "Направить", "findings_summary_ru": ["КРИТИЧ. test"]}
    en = localize_fz115_report(report, locale="en")
    assert en["locale"] == "en"
    assert "decision_en" in en


def test_webhook_signature_hmac():
    secret = "test-secret-key-12345"
    body = b'{"schema_version":"regulator-hub/v1","feeds":[]}'
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert hmac.compare_digest(sig, expected)


def test_circuit_breaker_degraded_response():
    cb = CollectorCircuitBreaker("opensanctions", failure_threshold=2, recovery_timeout_sec=60)
    cb.record_failure()
    cb.record_failure()
    assert cb.allow_request() is False
