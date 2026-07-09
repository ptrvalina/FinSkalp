"""Tests for event bus, circuit breaker, idempotency."""

from __future__ import annotations

import time

import pytest

from flowsint_crypto_compliance.infrastructure.circuit_breaker import CollectorCircuitBreaker, get_breaker
from flowsint_crypto_compliance.infrastructure.compliance_events import ComplianceEventBus
from flowsint_crypto_compliance.infrastructure.idempotency import IdempotencyStore, run_idempotent


def test_circuit_breaker_opens_after_failures():
    cb = CollectorCircuitBreaker("test-src", failure_threshold=3, recovery_timeout_sec=1.0)
    assert cb.allow_request() is True
    cb.record_failure()
    cb.record_failure()
    assert cb.allow_request() is True
    cb.record_failure()
    assert cb.allow_request() is False
    assert cb.status()["degraded"] is True
    time.sleep(1.1)
    assert cb.allow_request() is True


def test_circuit_breaker_registry():
    a = get_breaker("trongrid")
    b = get_breaker("trongrid")
    assert a is b


def test_event_bus_publish_and_recent():
    bus = ComplianceEventBus()
    ev = bus.publish("case_created", payload={"case_ref": "CASE-1"}, severity="info")
    assert ev["type"] == "case_created"
    recent = bus.recent(10)
    assert any(r["id"] == ev["id"] for r in recent)


def test_idempotency_store_dedupes():
    store = IdempotencyStore()
    key = "test-key-1"
    assert store.acquire("scope", key) == "new"
    store.complete("scope", key, {"ok": True})
    assert store.acquire("scope", key) == "done"
    assert store.get_result("scope", key) == {"ok": True}


def test_run_idempotent_executes_once():
    calls = {"n": 0}

    def work():
        calls["n"] += 1
        return {"v": calls["n"]}

    r1 = run_idempotent("t", "k1", work)
    r2 = run_idempotent("t", "k1", work)
    assert r1 == r2 == {"v": 1}
    assert calls["n"] == 1
