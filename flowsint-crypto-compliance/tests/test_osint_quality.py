"""Tests for FinSkalp OSINT quality upgrade (fusion, reliability, memory)."""

from flowsint_crypto_compliance.osint.fusion_confidence import EvidenceFinding, fuse_evidence
from flowsint_crypto_compliance.osint.institutional_memory import (
    cross_reference_closed_cases,
    extract_entities_from_osint,
    persist_osint_finding,
)
from flowsint_crypto_compliance.osint.source_reliability import (
    apply_source_reliability,
    record_analyst_feedback,
)


def test_bayesian_fusion_independent_vs_dependent():
    independent = fuse_evidence(
        [
            EvidenceFinding("explorer_tag", 0.8, source_name="TronScan"),
            EvidenceFinding("telegram", 0.7, source_name="@chan"),
        ]
    )
    dependent = fuse_evidence(
        [
            EvidenceFinding("darknet_index", 0.75, source_name="Ahmia", dependency_group="ahmia:q1"),
            EvidenceFinding("darknet_index", 0.72, source_name="Ahmia", dependency_group="ahmia:q1"),
        ]
    )
    assert independent.composite_confidence > dependent.composite_confidence
    assert independent.independent_groups == 2
    assert dependent.independent_groups == 1
    assert len([c for c in dependent.explain if c.included_in_fusion]) == 1


def test_fusion_error_probability_not_linear_sum():
    """Three moderate sources should not reach naive linear 100%."""
    result = fuse_evidence(
        [
            EvidenceFinding("web", 0.6, source_name="site1"),
            EvidenceFinding("forum", 0.6, source_name="forum1"),
            EvidenceFinding("telegram", 0.6, source_name="tg1"),
        ]
    )
    naive_linear = min(1.0, 0.6 + 0.6 + 0.6)
    assert result.composite_confidence < naive_linear
    assert 0.5 < result.composite_confidence < 0.95


def test_source_reliability_insufficient_sample():
    row = record_analyst_feedback(source_name="test_collector", confirmed=True)
    assert row.sample_size == 1
    assert row.insufficient_data is True
    rel = apply_source_reliability("test_collector", 0.8)
    assert 0.5 < rel < 0.8


def test_institutional_memory_inmem_cross_ref():
    tenant = "00000000-0000-0000-0000-000000000099"
    persist_osint_finding(
        tenant_id=tenant,
        case_id="11111111-1111-1111-1111-111111111111",
        case_ref="FS-CLOSED-001",
        entity_type="domain",
        entity_value="evil-shop.example",
        source_type="scalpel_extract",
        confidence=0.8,
    )
    entities = extract_entities_from_osint(
        {"aggregate": {"domains": ["evil-shop.example"]}},
        [],
    )
    mem = cross_reference_closed_cases(tenant_id=tenant, entities=entities)
    assert mem.checked_entities >= 1
    assert mem.has_prior_case_match
    assert mem.matches[0].prior_case_ref == "FS-CLOSED-001"


def test_health_snapshot_is_non_blocking():
    from flowsint_crypto_compliance.osint.collector_health import get_collector_health_snapshot

    snap = get_collector_health_snapshot()
    assert snap["status"] in ("warming", "ok", "degraded", "timeout")
    assert snap["source"] in ("snapshot", "cache")
    assert "collectors_total" in snap
