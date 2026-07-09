from flowsint_crypto_compliance.ingestion.registry_staging import stage_registry_lines
from flowsint_types.fiat_crypto import RegistrySource


def test_registry_staging_deduplicates_by_chain_address():
    lines = [
        '{"label_id":"a","source":"internal_osint","chain":"tron","address":"TX1","confidence":0.4}',
        '{"label_id":"b","source":"rosfinmonitoring","chain":"tron","address":"TX1","confidence":0.9,"sanctioned":true}',
    ]

    labels = stage_registry_lines(lines)

    assert len(labels) == 1
    assert labels[0].source == RegistrySource.ROSFINMONITORING
    assert labels[0].sanctioned is True


def test_registry_staging_keeps_highest_confidence_when_not_sanctioned():
    lines = [
        '{"label_id":"low","source":"internal_osint","chain":"eth","address":"0xabc","confidence":0.3}',
        '{"label_id":"high","source":"fiu","chain":"eth","address":"0xabc","confidence":0.85}',
    ]

    labels = stage_registry_lines(lines)

    assert len(labels) == 1
    assert labels[0].confidence == 0.85
    assert labels[0].source == RegistrySource.FIU
