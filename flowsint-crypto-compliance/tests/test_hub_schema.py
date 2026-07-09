import pytest

from flowsint_crypto_compliance.schemas.hub import (
    hub_row_to_bank_feed,
    validate_bank_feed_batch,
    validate_registry_label_row,
)


def test_bank_feed_batch_validates():
    payload = {
        "schema_version": "regulator-hub/v1",
        "hub_id": "cbr-fiu-hub",
        "feeds": [
            {
                "feed_id": "b-001",
                "bank_name": "Sber",
                "region": "RU",
                "currency": "RUB",
                "amount": 100000,
                "alert_type": "crypto_suspicion",
                "reported_at": "2026-06-30T12:00:00Z",
            }
        ],
    }
    validate_bank_feed_batch(payload)
    feed = hub_row_to_bank_feed(payload["feeds"][0])
    assert feed.region == "RU"
    assert feed.bank_name == "Sber"


def test_bank_feed_batch_rejects_invalid_region():
    with pytest.raises(ValueError, match="Invalid bank feed batch"):
        validate_bank_feed_batch(
            {
                "schema_version": "regulator-hub/v1",
                "feeds": [
                    {
                        "feed_id": "x",
                        "region": "RUSSIA",
                        "reported_at": "2026-06-30T12:00:00Z",
                    }
                ],
            }
        )


def test_registry_label_row_validates():
    validate_registry_label_row(
        {
            "source": "rosfinmonitoring",
            "chain": "tron",
            "address": "TWalletRU123456789012345678901234",
            "entity_name": "Криптомиксер",
            "sanctioned": True,
            "list_reference": "Перечень 115-ФЗ",
            "confidence": 0.9,
        }
    )
