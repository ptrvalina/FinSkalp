from __future__ import annotations

from pathlib import Path

from flowsint_types.fiat_crypto import (
    BankRegulatorFeed,
    ControlPurchaseEvent,
    FiatLegEvent,
    LicensedPlatformEvent,
    SovereignRiskLabel,
)

from ..osint_core.fusion_engine import InvestigationBundle, OSINTFusionEngine
from .bank_regulator import BankRegulatorConnector, bank_feed_to_fiat_event
from .sovereign_registry import parse_registry_jsonl
from .parsers import parse_control_purchase_row, parse_licensed_platform_row


class HubIngestPipeline:
    """
    Unified ingest pipeline for regulator case building (hub bank feed).

    Platform v2 canonical ingest lives in ``platform/v2/ingest_pipeline.py``.
    This class is aliased as ``IngestPipeline`` for backward compatibility.
    """

    def __init__(self, engine: OSINTFusionEngine | None = None):
        self._engine = engine or OSINTFusionEngine()

    @property
    def engine(self) -> OSINTFusionEngine:
        return self._engine

    def build_bundle(
        self,
        case_id: str,
        *,
        bank_connector: BankRegulatorConnector | None = None,
        licensed_path: Path | None = None,
        control_path: Path | None = None,
        registry_path: Path | None = None,
        extra_fiat: list[FiatLegEvent] | None = None,
    ) -> InvestigationBundle:
        bank_feeds: list[BankRegulatorFeed] = []
        if bank_connector:
            bank_feeds = list(bank_connector.fetch_feeds(case_id=case_id))

        fiat_events = [bank_feed_to_fiat_event(b) for b in bank_feeds]
        if extra_fiat:
            fiat_events.extend(extra_fiat)

        licensed: list[LicensedPlatformEvent] = []
        if licensed_path and licensed_path.exists():
            licensed = _load_jsonl(licensed_path, parse_licensed_platform_row)

        controls: list[ControlPurchaseEvent] = []
        if control_path and control_path.exists():
            controls = _load_jsonl(control_path, parse_control_purchase_row)

        registry_labels: list[SovereignRiskLabel] = []
        if registry_path and registry_path.exists():
            registry_labels = parse_registry_jsonl(registry_path)
            for label in registry_labels:
                self._engine.label_cache.put(label)

        return InvestigationBundle(
            case_id=case_id,
            bank_feeds=bank_feeds,
            fiat_events=fiat_events,
            licensed_events=licensed,
            control_purchases=controls,
            registry_labels=registry_labels,
        )


def _load_jsonl(path: Path, parser):
    import json

    items = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(parser(json.loads(line)))
    return items


# Backward-compatible alias — platform v2 ingest is platform/v2/ingest_pipeline.py
IngestPipeline = HubIngestPipeline
