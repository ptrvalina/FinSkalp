"""Build regulator-hub JSON rows from typed bank feeds (omit null optional fields)."""

from __future__ import annotations

from typing import Any

from flowsint_types.fiat_crypto import BankRegulatorFeed


def bank_feed_to_hub_row(feed: BankRegulatorFeed) -> dict[str, Any]:
    row: dict[str, Any] = {
        "feed_id": feed.feed_id,
        "region": feed.region,
        "reported_at": feed.observed_at or "2026-06-30T12:00:00Z",
    }
    if feed.case_id:
        row["case_id"] = feed.case_id
    if feed.bank_bic:
        row["bank_bic"] = feed.bank_bic
    if feed.bank_name:
        row["bank_name"] = feed.bank_name
    if feed.alert_type:
        row["alert_type"] = feed.alert_type
    if feed.currency:
        row["currency"] = feed.currency
    if feed.amount is not None:
        row["amount"] = feed.amount
    if feed.payment_reference:
        row["payment_reference"] = feed.payment_reference
    if feed.counterparty_hint:
        row["counterparty_hint"] = feed.counterparty_hint
    if feed.linked_crypto_address and len(feed.linked_crypto_address) >= 26:
        row["linked_crypto_address"] = feed.linked_crypto_address
    if feed.linked_chain:
        row["linked_chain"] = feed.linked_chain.value
    if feed.subject_id:
        row["subject_id"] = feed.subject_id
    return row
