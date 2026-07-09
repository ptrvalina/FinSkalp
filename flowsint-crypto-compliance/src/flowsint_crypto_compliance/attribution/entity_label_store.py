"""Accumulative entity label store (in-memory + optional Postgres)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.attribution.types import SOURCE_PRIORITY, EntityLabel

_store: "EntityLabelStore | None" = None


class EntityLabelStore:
  def __init__(self) -> None:
      self._labels: dict[str, EntityLabel] = {}

  def _key(self, chain: str, address: str) -> str:
      norm = address.lower() if chain == "eth" else address.strip()
      return f"{chain.lower()}:{norm}"

  def upsert(self, label: EntityLabel, *, force: bool = False) -> bool:
      key = self._key(label.chain, label.address)
      existing = self._labels.get(key)
      if existing and not force:
          if existing.tier < label.tier:
              return False
          if existing.tier == label.tier:
              ex_pri = SOURCE_PRIORITY.get(existing.source, 99)
              new_pri = SOURCE_PRIORITY.get(label.source, 99)
              if ex_pri < new_pri or (
                  ex_pri == new_pri and existing.confidence >= label.confidence
              ):
                  return False
      self._labels[key] = label
      try:
          from flowsint_crypto_compliance.platform.v2.entity_label_bridge import sync_entity_label_to_kg

          sync_entity_label_to_kg(label)
      except Exception:
          pass
      return True

  def lookup(self, chain: str, address: str) -> EntityLabel | None:
      lbl = self._labels.get(self._key(chain, address))
      if lbl and lbl.rejected:
          return None
      return lbl

  def lookup_map(self, chain: str, addresses: list[str]) -> dict[str, EntityLabel]:
      return {a: lbl for a in addresses if (lbl := self.lookup(chain, a))}

  def bulk_upsert(self, labels: list[EntityLabel]) -> int:
      n = 0
      for lbl in labels:
          if self.upsert(lbl):
              n += 1
      return n

  def all_labels(self) -> list[EntityLabel]:
      return list(self._labels.values())

  def count(self) -> int:
      return len(self._labels)

  def to_sovereign_dict(self, label: EntityLabel) -> dict[str, Any]:
      from flowsint_types.fiat_crypto import Chain, RegistrySource, SovereignRiskLabel

      source_map = {
          "ofac_sdn": RegistrySource.OTHER,
          "opensanctions": RegistrySource.OTHER,
          "graphsense": RegistrySource.INTERNAL_OSINT,
          "tronscan": RegistrySource.INTERNAL_OSINT,
          "cospend_cluster": RegistrySource.INTERNAL_OSINT,
          "kyt_import": RegistrySource.INTERNAL_OSINT,
          "sovereign_registry": RegistrySource.ROSFINMONITORING,
      }
      return SovereignRiskLabel(
          label_id=f"entity-{label.chain}-{label.address[:12]}-{label.source}",
          source=source_map.get(label.source, RegistrySource.INTERNAL_OSINT),
          chain=Chain(label.chain),
          address=label.address,
          entity_name=label.label,
          category=label.category,
          risk_score=label.risk_score,
          confidence=label.confidence,
          sanctioned=label.sanctioned,
          list_reference=label.source,
          cluster_ref=label.cluster_ref,
          snapshot_at=label.added_at.isoformat(),
      )


def get_entity_label_store() -> EntityLabelStore:
    global _store
    if _store is None:
        from flowsint_crypto_compliance.demo.combat_mode import resolve_entity_store_mode

        mode = resolve_entity_store_mode()
        if mode == "postgres" and os.getenv("DATABASE_URL"):
            try:
                from flowsint_crypto_compliance.attribution.postgres_entity_store import (
                    PostgresEntityLabelStore,
                )

                _store = PostgresEntityLabelStore()
            except Exception as exc:
                import logging

                logging.getLogger(__name__).warning(
                    "Postgres entity store unavailable (%s); using in-memory store",
                    exc.__class__.__name__,
                )
                _store = EntityLabelStore()
        else:
            _store = EntityLabelStore()
    return _store


def reset_entity_label_store() -> None:
    """Test helper — clear singleton."""
    global _store
    _store = None


def persist_to_postgres(store: EntityLabelStore, db_session: Any) -> int:
    """Upsert labels into compliance_entity_labels when DB available."""
    try:
        from flowsint_crypto_compliance.storage.db_models import ComplianceEntityLabel
        from sqlalchemy.dialects.postgresql import insert
    except Exception:
        return 0
    count = 0
    for lbl in store.all_labels():
        stmt = (
            insert(ComplianceEntityLabel)
            .values(
                chain=lbl.chain,
                address=lbl.address.lower() if lbl.chain == "eth" else lbl.address,
                label=lbl.label,
                category=lbl.category,
                confidence=lbl.confidence,
                source=lbl.source,
                tier=lbl.tier,
                risk_score=lbl.risk_score,
                sanctioned=lbl.sanctioned,
                cluster_ref=lbl.cluster_ref,
                evidence=lbl.evidence,
                added_at=lbl.added_at or datetime.now(timezone.utc),
            )
            .on_conflict_do_update(
                index_elements=["chain", "address"],
                set_={
                    "label": lbl.label,
                    "category": lbl.category,
                    "confidence": lbl.confidence,
                    "source": lbl.source,
                    "tier": lbl.tier,
                    "risk_score": lbl.risk_score,
                    "sanctioned": lbl.sanctioned,
                    "cluster_ref": lbl.cluster_ref,
                    "evidence": lbl.evidence,
                },
            )
        )
        db_session.execute(stmt)
        count += 1
    db_session.flush()
    return count
