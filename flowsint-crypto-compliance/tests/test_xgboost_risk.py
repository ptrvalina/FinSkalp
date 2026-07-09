from flowsint_crypto_compliance.detection.findings import IllegalFlowFinding
from flowsint_crypto_compliance.detection.illegal_flow import IllegalFlowDetector
from flowsint_crypto_compliance.engine.xgboost_risk import SovereignRiskModel, extract_case_features
from flowsint_types.fiat_crypto import Chain, FusedAttribution


def test_xgboost_raises_score_for_sanctioned_wallet():
    model = SovereignRiskModel()
    findings = [
        IllegalFlowFinding(
            severity="critical",
            code="SANCTIONS_LIST_HIT",
            title_ru="test",
            description_ru="test",
            confidence=0.95,
        )
    ]
    attributions = [
        FusedAttribution(
            attribution_id="a1",
            address="TRU_TEST",
            chain=Chain.TRON,
            primary_region="RU",
            sanctioned=True,
            confidence=0.95,
        )
    ]
    result = model.score_case(
        findings=findings,
        attributions=attributions,
        bridges=[],
        bank_feed_count=1,
        control_purchase_count=1,
        heuristic_score=70.0,
    )
    assert result.score >= 70.0
    assert result.model_version == "sovereign-xgb-v1"
    assert "sanctioned_wallets" in result.features


def test_illegal_flow_detector_returns_xgboost_metadata():
    detector = IllegalFlowDetector(use_xgboost=True)
    findings, score, meta = detector.analyze(
        attributions=[
            FusedAttribution(
                attribution_id="a2",
                address="TRU_MIXER",
                chain=Chain.TRON,
                primary_region="RU",
                sanctioned=True,
                black_zone=True,
                confidence=0.9,
            )
        ],
        bridges=[],
        bank_feed_count=1,
        control_purchase_count=1,
    )
    assert findings
    assert score >= 50
    assert "xgboost" in meta


def test_extract_case_features_counts_registry_hits():
    features = extract_case_features(
        findings=[],
        attributions=[
            FusedAttribution(
                attribution_id="a3",
                address="TRU_REG",
                chain=Chain.TRON,
                watchlist_label="mixer",
                label_source="rosfinmonitoring",
                confidence=0.8,
            )
        ],
        bridges=[],
        bank_feed_count=0,
        control_purchase_count=0,
    )
    assert features["registry_hits"] == 1.0
