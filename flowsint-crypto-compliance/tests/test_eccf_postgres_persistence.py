"""Wave 2 — ECCF Postgres persistence + hash-chained audit (feature-flagged)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from flowsint_crypto_compliance import feature_flags
from flowsint_crypto_compliance.platform.v2.eccf.audit_trail import AuditAction, reset_audit_trail
from flowsint_crypto_compliance.platform.v2.eccf.hash_chain import (
    compute_entry_hash,
    genesis_hash,
    verify_chain,
)
from flowsint_crypto_compliance.platform.v2.eccf.repository import (
    ECCFRepository,
    get_eccf_repository,
    reset_eccf_repository,
)

_ENV = "FINSKALP_ECCF_POSTGRES_PERSISTENCE"


@pytest.fixture(autouse=True)
def _legacy_eccf_store(monkeypatch):
    """Ensure Wave 2 flag is off unless a test explicitly enables it."""
    monkeypatch.delenv(_ENV, raising=False)
    reset_eccf_repository()
    reset_audit_trail()
    yield
    reset_eccf_repository()
    reset_audit_trail()


# --- hash chain (pure, no DB) -------------------------------------------------


def test_genesis_hash_is_fixed():
    assert len(genesis_hash()) == 64
    assert genesis_hash() == "0" * 64


def test_hash_chain_links_entries():
    ts = datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)
    h1 = compute_entry_hash(
        evidence_id="EV-1",
        action="Created",
        actor="test",
        timestamp=ts,
        details={"k": "v"},
        prev_hash=genesis_hash(),
    )
    h2 = compute_entry_hash(
        evidence_id="EV-1",
        action="Validated",
        actor="test",
        timestamp=ts,
        details={},
        prev_hash=h1,
    )
    assert h1 != h2
    result = verify_chain(
        [
            {
                "evidence_id": "EV-1",
                "action": "Created",
                "actor": "test",
                "timestamp": ts,
                "details": {"k": "v"},
                "prev_hash": genesis_hash(),
                "entry_hash": h1,
            },
            {
                "evidence_id": "EV-1",
                "action": "Validated",
                "actor": "test",
                "timestamp": ts,
                "details": {},
                "prev_hash": h1,
                "entry_hash": h2,
            },
        ]
    )
    assert result["ok"] is True


def test_hash_chain_detects_tampering():
    ts = datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)
    h1 = compute_entry_hash(
        evidence_id="EV-1",
        action="Created",
        actor="test",
        timestamp=ts,
        details={},
        prev_hash=genesis_hash(),
    )
    result = verify_chain(
        [
            {
                "evidence_id": "EV-1",
                "action": "Created",
                "actor": "test",
                "timestamp": ts,
                "details": {},
                "prev_hash": genesis_hash(),
                "entry_hash": "deadbeef" * 8,
            }
        ]
    )
    assert result["ok"] is False
    assert result["errors"]


# --- feature flag factory -----------------------------------------------------


def test_eccf_repository_defaults_to_in_memory():
    assert isinstance(get_eccf_repository(), ECCFRepository)


def test_eccf_repository_selects_postgres_when_flag_on(monkeypatch):
    monkeypatch.setenv(_ENV, "1")
    reset_eccf_repository()
    from flowsint_crypto_compliance.platform.v2.eccf.postgres_store import (
        PostgresECCFRepository,
    )

    repo = get_eccf_repository()
    assert isinstance(repo, PostgresECCFRepository)


def test_eccf_flag_in_registry():
    snap = feature_flags.flag_snapshot()
    assert "eccf_postgres_persistence" in snap
    assert snap["eccf_postgres_persistence"]["env_var"] == _ENV
    assert snap["eccf_postgres_persistence"]["default"] is False
