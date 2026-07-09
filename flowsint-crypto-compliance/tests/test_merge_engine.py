from flowsint_crypto_compliance.osint_core.merge_engine import MergeEngine
from flowsint_types.fiat_crypto import EntityKind


def test_merge_engine_sanctioned_registry_boosts_confidence():
    engine = MergeEngine()
    decision = engine.merge(
        address="TRU_SANCTIONED",
        sovereign_label=None,
        sovereign_confidence=0.4,
        sovereign_region="RU",
        sovereign_kind=EntityKind.UNKNOWN,
        sovereign_evidence=["blockchain_public:region_RU=1.0"],
        registry_entity="Криптомиксер (перечень 115-ФЗ)",
        registry_source="rosfinmonitoring",
        registry_confidence=0.9,
        registry_disputed=False,
        registry_category="mixer",
        registry_sanctioned=True,
        registry_list_reference="Перечень 115-ФЗ",
        linkage_strength=0.0,
        bank_linked=False,
    )

    assert decision.sanctioned is True
    assert decision.confidence >= 0.96
    assert any("registry:sanctioned" in e for e in decision.evidence_chain)


def test_merge_engine_domestic_wins_disputed_registry():
    engine = MergeEngine()
    decision = engine.merge(
        address="TRU_DISPUTED",
        sovereign_label="otc_hub_ru",
        sovereign_confidence=0.7,
        sovereign_region="RU",
        sovereign_kind=EntityKind.OTC,
        sovereign_evidence=["control_purchase"],
        registry_entity="Зарубежная биржа",
        registry_source="cis_partner",
        registry_confidence=0.95,
        registry_disputed=True,
        registry_category="exchange",
        linkage_strength=0.5,
        bank_linked=False,
    )

    assert decision.disputed is True
    assert decision.sovereign_label == "otc_hub_ru"
    assert any("domestic_wins_disputed_registry" in e for e in decision.evidence_chain)


def test_merge_engine_registry_supplements_unknown_sovereign():
    engine = MergeEngine()
    decision = engine.merge(
        address="TRU_OTC",
        sovereign_label=None,
        sovereign_confidence=0.3,
        sovereign_region="RU",
        sovereign_kind=EntityKind.UNKNOWN,
        sovereign_evidence=["blockchain_public:region_RU=1.0"],
        registry_entity="Серый OTC-узел",
        registry_source="internal_osint",
        registry_confidence=0.8,
        registry_disputed=False,
        registry_category="otc",
        linkage_strength=0.0,
        bank_linked=False,
    )

    assert decision.watchlist_label == "Серый OTC-узел"
    assert decision.entity_kind == EntityKind.OTC
    assert any("merge:registry_supplement" in e for e in decision.evidence_chain)


def test_merge_engine_bank_linkage_boosts_confidence():
    engine = MergeEngine()
    decision = engine.merge(
        address="TRU_LINKED",
        sovereign_label="hub_ru",
        sovereign_confidence=0.55,
        sovereign_region="RU",
        sovereign_kind=EntityKind.OTC,
        sovereign_evidence=["behavioral_heuristic:high_fan_in_fan_out"],
        registry_entity=None,
        registry_source=None,
        registry_confidence=0.0,
        registry_disputed=False,
        registry_category=None,
        linkage_strength=0.8,
        bank_linked=True,
    )

    assert decision.confidence > 0.55
    assert any(e.startswith("bank_linkage:") for e in decision.evidence_chain)
