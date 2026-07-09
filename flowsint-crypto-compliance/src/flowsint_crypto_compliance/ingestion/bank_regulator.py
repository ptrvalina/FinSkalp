from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterator

from flowsint_types.fiat_crypto import BankRegulatorFeed, Chain, EvidenceSource, FiatLegEvent

from ..ingestion.parsers import parse_fiu_alert_row


class BankRegulatorConnector(ABC):
    """Interface for bank data delivered via government regulator hub."""

    @abstractmethod
    def fetch_feeds(self, *, since: str | None = None, case_id: str | None = None) -> Iterator[BankRegulatorFeed]:
        ...


class FileBankRegulatorConnector(BankRegulatorConnector):
    """Load bank feeds from regulator-exported JSONL (MVP / air-gap)."""

    def __init__(self, path: Path):
        self._path = path

    def fetch_feeds(
        self, *, since: str | None = None, case_id: str | None = None
    ) -> Iterator[BankRegulatorFeed]:
        with self._path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if case_id and row.get("case_id") != case_id:
                    continue
                if since and (row.get("observed_at") or "") < since:
                    continue
                yield _parse_bank_feed_row(row)


class RegulatorAPIConnector(BankRegulatorConnector):
    """
    Stub for future regulator API integration.

    Banks push STR/CTR to regulator hub → this connector pulls normalized feeds.
  """

    def __init__(self, base_url: str, api_token: str | None = None):
        self._base_url = base_url
        self._token = api_token

    def fetch_feeds(
        self, *, since: str | None = None, case_id: str | None = None
    ) -> Iterator[BankRegulatorFeed]:
        # Placeholder: implement when regulator API contract is signed
        return iter([])


def bank_feed_to_fiat_event(feed: BankRegulatorFeed) -> FiatLegEvent:
    """Convert regulator hub bank feed to FiatLegEvent for bridge tracing."""
    return FiatLegEvent(
        event_id=f"bank-{feed.feed_id}",
        source=EvidenceSource.BANK_REGULATOR_HUB,
        region=feed.region,
        currency=feed.currency,
        amount=feed.amount,
        bank_reference=feed.payment_reference,
        platform_id=feed.counterparty_hint,
        subject_id=feed.subject_id,
        observed_at=feed.observed_at,
        raw_summary=f"{feed.alert_type or 'alert'} via {feed.bank_name or feed.bank_bic}",
    )


def _parse_bank_feed_row(row: dict[str, Any]) -> BankRegulatorFeed:
    chain = row.get("linked_chain")
    return BankRegulatorFeed(
        feed_id=str(row["feed_id"]),
        bank_bic=row.get("bank_bic"),
        bank_name=row.get("bank_name"),
        alert_type=row.get("alert_type"),
        region=str(row["region"]),
        currency=row.get("currency"),
        amount=_float_or_none(row.get("amount")),
        payment_reference=row.get("payment_reference"),
        counterparty_hint=row.get("counterparty_hint"),
        linked_crypto_address=row.get("linked_crypto_address"),
        linked_chain=Chain(chain.lower()) if chain else None,
        subject_id=row.get("subject_id"),
        case_id=row.get("case_id"),
        observed_at=row.get("observed_at"),
    )


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
