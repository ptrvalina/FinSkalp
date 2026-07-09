from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema
from jsonschema import Draft202012Validator

def _schema_dir() -> Path:
    bundled = Path(__file__).resolve().parent / "json_schemas"
    if bundled.is_dir():
        return bundled
    repo = Path(__file__).resolve().parents[3] / "schemas"
    if repo.is_dir():
        return repo
    raise FileNotFoundError("Compliance JSON schemas not found")


def _load_schema(name: str) -> dict[str, Any]:
    with (_schema_dir() / name).open(encoding="utf-8") as f:
        return json.load(f)


def get_bank_feed_validator() -> Draft202012Validator:
    feed_schema = _load_schema("regulator_hub_v1_bank_feed.schema.json")
    batch_schema = _load_schema("regulator_hub_v1_bank_feed_batch.schema.json")
    store = {
        feed_schema["$id"]: feed_schema,
        batch_schema["$id"]: batch_schema,
    }
    resolver = jsonschema.RefResolver(base_uri=batch_schema["$id"], referrer=batch_schema, store=store)
    return Draft202012Validator(batch_schema, resolver=resolver)


def get_registry_label_validator() -> Draft202012Validator:
    return Draft202012Validator(_load_schema("registry_label_v1.schema.json"))


def validate_bank_feed_batch(payload: dict[str, Any]) -> None:
    validator = get_bank_feed_validator()
    errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
    if errors:
        msg = "; ".join(f"{list(e.path)}: {e.message}" for e in errors[:5])
        raise ValueError(f"Invalid bank feed batch: {msg}")


def validate_registry_label_row(payload: dict[str, Any]) -> None:
    validator = get_registry_label_validator()
    errors = list(validator.iter_errors(payload))
    if errors:
        raise ValueError(errors[0].message)


def hub_row_to_bank_feed(row: dict[str, Any]):
    """Map regulator hub JSON row to BankRegulatorFeed."""
    from flowsint_types.fiat_crypto import BankRegulatorFeed, Chain

    chain = row.get("linked_chain")
    observed = row.get("reported_at") or row.get("ingested_at")
    return BankRegulatorFeed(
        feed_id=str(row["feed_id"]),
        bank_bic=row.get("bank_bic"),
        bank_name=row.get("bank_name"),
        alert_type=row.get("alert_type"),
        region=str(row["region"]),
        currency=row.get("currency"),
        amount=row.get("amount"),
        payment_reference=row.get("payment_reference"),
        counterparty_hint=row.get("counterparty_hint"),
        linked_crypto_address=row.get("linked_crypto_address"),
        linked_chain=Chain(chain.lower()) if chain else None,
        subject_id=row.get("subject_id"),
        case_id=row.get("case_id"),
        observed_at=observed,
    )
