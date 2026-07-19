"""Tests for RFC-15 multi-dimensional confidence decomposition."""

from flowsint_crypto_compliance.platform.v2.multi_dimensional_confidence import (
    ConfidenceDimensions,
    build_confidence_dimensions,
)


def test_build_confidence_dimensions_minimal_screening():
    screening = {
        "risk_score": 72.5,
        "confidence": 0.6,
        "findings": [
            {
                "code": "REGISTRY_HIGH_RISK_LABEL",
                "title_ru": "Реестр 115-ФЗ",
                "category": "mixer",
                "confidence": 0.85,
            }
        ],
        "evidence_chain": ["registry:rosfin:tron:addr123", "onchain:tron:in=2:out=5"],
        "source_status": {"registry_primary": "hit", "onchain": "ok"},
        "onchain_summary": {
            "counterparties": 4,
            "kyt_exposure": {"connection_count": 3},
        },
    }
    dims = build_confidence_dimensions(screening)
    assert isinstance(dims, ConfidenceDimensions)
    assert dims.aggregate_risk_score == 72.5
    assert 0.0 <= dims.identity_confidence <= 1.0
    assert 0.0 <= dims.evidence_strength <= 1.0
    assert 0.0 <= dims.relationship_confidence <= 1.0
    assert 0.0 <= dims.source_reliability <= 1.0
    assert "formula_ru" in dims.explain_ru


def test_build_confidence_dimensions_with_attribution():
    screening = {
        "risk_score": 55.0,
        "confidence": 0.5,
        "findings": [],
        "evidence_chain": ["wallet:eth:0xabc"],
        "source_status": {"registry_primary": "miss"},
        "onchain_summary": {},
    }
    attribution = {
        "primary_label": {"label": "Exchange hub", "confidence": 0.78},
        "linkage_scores": [0.6, 0.7],
    }
    dims = build_confidence_dimensions(screening, attribution=attribution)
    assert dims.identity_confidence >= 0.7
    assert dims.relationship_confidence >= 0.4
    dumped = dims.model_dump()
    assert set(dumped) >= {
        "identity_confidence",
        "evidence_strength",
        "relationship_confidence",
        "source_reliability",
        "aggregate_risk_score",
        "explain_ru",
    }


def test_build_confidence_dimensions_empty_defaults():
    dims = build_confidence_dimensions({})
    assert dims.aggregate_risk_score == 0.0
    assert dims.explain_ru["composite_confidence"] is not None
