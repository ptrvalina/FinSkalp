"""Analyst confirm/reject attribution + postgres entity store."""

from __future__ import annotations

import pytest

from flowsint_crypto_compliance.attribution.entity_label_store import (
    EntityLabelStore,
    reset_entity_label_store,
)
from flowsint_crypto_compliance.attribution.postgres_entity_store import (
    analyst_confirm_label,
    analyst_reject_label,
)
from flowsint_crypto_compliance.attribution.types import EntityLabel, TIER_ANALYST_CONFIRMED


def test_analyst_confirm_promotes_tier1():
    reset_entity_label_store()
    store = EntityLabelStore()
    store.upsert(
        EntityLabel(
            address="TAddrA11111111111111111111111111111",
            chain="tron",
            label="Bybit",
            category="exchange",
            confidence=0.65,
            source="cospend_cluster",
            tier=2,
        )
    )
    reset_entity_label_store()
    import flowsint_crypto_compliance.attribution.entity_label_store as els

    els._store = store  # type: ignore[attr-defined]

    lbl = analyst_confirm_label(
        chain="tron",
        address="TAddrA11111111111111111111111111111",
        label="Bybit",
        category="exchange",
        analyst_id="analyst-1",
    )
    assert lbl.tier == TIER_ANALYST_CONFIRMED
    assert lbl.source == "analyst_confirmed"
    assert lbl.confidence == 1.0

    # Co-spend sibling inherits via store lookup
    store.upsert(
        EntityLabel(
            address="TAddrB2222222222222222222222222222222",
            chain="tron",
            label="Bybit",
            category="exchange",
            confidence=0.65,
            source="cospend_cluster",
            tier=2,
            cluster_ref="cluster-bybit",
        )
    )
    confirmed = store.lookup("tron", "TAddrA11111111111111111111111111111")
    assert confirmed is not None
    assert confirmed.tier == 1


def test_analyst_reject_excluded_from_lookup():
    reset_entity_label_store()
    store = EntityLabelStore()
    reset_entity_label_store()
    import flowsint_crypto_compliance.attribution.entity_label_store as els

    els._store = store  # type: ignore[attr-defined]
    analyst_reject_label(
        chain="tron",
        address="TReject333333333333333333333333333333",
        label="FakeExchange",
        category="exchange",
        analyst_id="analyst-1",
    )
    assert store.lookup("tron", "TReject333333333333333333333333333333") is None
    all_lbl = store._labels.get("tron:TReject333333333333333333333333333333")
    assert all_lbl is not None
    assert all_lbl.status == "rejected"
