from __future__ import annotations

from typing import Any

from flowsint_types.fiat_crypto import Chain, EvidenceSource, FiatLegEvent


def parse_fiu_alert_row(row: dict[str, Any]) -> FiatLegEvent:
    """Parse a normalized FIU/bank alert row from regulator feed (CSV/JSON)."""
    return FiatLegEvent(
        event_id=str(row["event_id"]),
        source=EvidenceSource(row.get("source", EvidenceSource.FIU_ALERT.value)),
        region=row.get("region"),
        currency=row.get("currency"),
        amount=_float_or_none(row.get("amount")),
        bank_reference=row.get("bank_reference"),
        platform_id=row.get("platform_id"),
        subject_id=row.get("subject_id"),
        observed_at=row.get("observed_at"),
        raw_summary=row.get("summary"),
    )


def parse_licensed_platform_row(row: dict[str, Any]) -> "LicensedPlatformEvent":
    from flowsint_types.fiat_crypto import LicensedPlatformEvent

    return LicensedPlatformEvent(
        event_id=str(row["event_id"]),
        platform_name=str(row["platform_name"]),
        platform_license_id=row.get("platform_license_id"),
        region=row.get("region"),
        direction=str(row["direction"]).lower(),
        chain=Chain(str(row["chain"]).lower()),
        address=str(row["address"]),
        amount_crypto=_float_or_none(row.get("amount_crypto")),
        asset=row.get("asset"),
        amount_fiat=_float_or_none(row.get("amount_fiat")),
        currency=row.get("currency"),
        user_ref=row.get("user_ref"),
        observed_at=row.get("observed_at"),
    )


def parse_control_purchase_row(row: dict[str, Any]) -> "ControlPurchaseEvent":
    from flowsint_types.fiat_crypto import ControlPurchaseEvent

    return ControlPurchaseEvent(
        event_id=str(row["event_id"]),
        operator_ref=str(row["operator_ref"]),
        region=str(row["region"]),
        channel=str(row["channel"]),
        chain=Chain(str(row["chain"]).lower()),
        source_address=row.get("source_address"),
        target_address=str(row["target_address"]),
        asset=row.get("asset"),
        amount_fiat=_float_or_none(row.get("amount_fiat")),
        currency=row.get("currency"),
        observed_at=row.get("observed_at"),
        notes=row.get("notes"),
    )


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
