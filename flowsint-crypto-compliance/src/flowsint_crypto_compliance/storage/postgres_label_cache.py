from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from flowsint_types.fiat_crypto import Chain, RegistrySource, SovereignRiskLabel

from .db_models import ComplianceRegistryLabel
from .label_cache import LabelCache


class PostgresLabelCache(LabelCache):
    """PostgreSQL-backed store for the sovereign RF/CIS risk-label registry."""

    def __init__(self, db: Session):
        super().__init__()
        self._db = db

    def put(self, label: SovereignRiskLabel) -> None:
        super().put(label)
        stmt = (
            insert(ComplianceRegistryLabel)
            .values(
                chain=label.chain.value,
                address=_normalize_address(label.chain, label.address),
                source=label.source.value,
                entity_name=label.entity_name,
                category=label.category,
                risk_score=label.risk_score,
                confidence=label.confidence,
                sanctioned=label.sanctioned,
                list_reference=label.list_reference,
                disputed=label.disputed,
                snapshot_at=label.snapshot_at,
                cluster_ref=label.cluster_ref,
                label_id=label.label_id,
            )
            .on_conflict_do_update(
                index_elements=["chain", "address"],
                set_={
                    "source": label.source.value,
                    "entity_name": label.entity_name,
                    "category": label.category,
                    "risk_score": label.risk_score,
                    "confidence": label.confidence,
                    "sanctioned": label.sanctioned,
                    "list_reference": label.list_reference,
                    "disputed": label.disputed,
                    "snapshot_at": label.snapshot_at,
                    "cluster_ref": label.cluster_ref,
                    "label_id": label.label_id,
                },
            )
        )
        self._db.execute(stmt)

    def lookup(self, chain: Chain, address: str) -> SovereignRiskLabel | None:
        mem = super().lookup(chain, address)
        if mem:
            return mem
        row = self._db.execute(
            select(ComplianceRegistryLabel).where(
                ComplianceRegistryLabel.chain == chain.value,
                ComplianceRegistryLabel.address == _normalize_address(chain, address),
            )
        ).scalar_one_or_none()
        if not row:
            return None
        label = _row_to_label(row)
        super().put(label)
        return label

    def bulk_upsert(self, labels: list[SovereignRiskLabel]) -> int:
        count = 0
        for label in labels:
            self.put(label)
            count += 1
        self._db.flush()
        return count

    def count(self) -> int:
        return self._db.query(ComplianceRegistryLabel).count()


def _normalize_address(chain: Chain, address: str) -> str:
    return address.lower() if chain == Chain.ETH else address.strip()


def _row_to_label(row: ComplianceRegistryLabel) -> SovereignRiskLabel:
    return SovereignRiskLabel(
        label_id=row.label_id,
        source=RegistrySource(row.source),
        chain=Chain(row.chain),
        address=row.address,
        entity_name=row.entity_name,
        category=row.category,
        risk_score=row.risk_score,
        confidence=row.confidence,
        sanctioned=row.sanctioned,
        list_reference=row.list_reference,
        disputed=row.disputed,
        snapshot_at=row.snapshot_at,
        cluster_ref=row.cluster_ref,
    )
