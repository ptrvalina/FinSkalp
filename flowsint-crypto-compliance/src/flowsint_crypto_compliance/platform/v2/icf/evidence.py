"""RFC-0014 Ch.8 — evidence generator."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.platform.v2.canonical import Evidence, TrustLevel
from flowsint_crypto_compliance.platform.v2.evidence_center import content_hash_from_finding


class EvidenceGenerator:
    """Generate canonical Evidence records from normalized ICF data."""

    def generate(
        self,
        records: list[dict[str, Any]],
        *,
        tenant_id: uuid.UUID,
        connector_id: str,
        case_ref: str | None = None,
        acquisition_method: str = "icf_automated_collection",
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for rec in records:
            et = str(rec.get("entity_type") or "unknown")
            ev = str(rec.get("entity_value") or "")
            source_type = str(rec.get("source_type") or connector_id)
            payload = rec.get("payload") if isinstance(rec.get("payload"), dict) else rec
            content_hash = content_hash_from_finding(
                entity_type=et,
                entity_value=ev,
                source_type=source_type,
                payload=payload,
            )
            confidence = float(rec.get("confidence") or 0.5)
            evidence = Evidence(
                tenant_id=tenant_id,
                source_type=source_type,
                content_hash=content_hash,
                discovered_at=datetime.now(timezone.utc),
                trust=TrustLevel(
                    source_reliability=min(1.0, confidence + 0.05),
                    information_credibility=confidence,
                    sample_size=1,
                ),
                payload={
                    **(payload or {}),
                    "entity_type": et,
                    "entity_value": ev,
                    "case_ref": case_ref,
                    "connector_id": connector_id,
                },
                acquisition_method=acquisition_method,
                original_uri=rec.get("original_uri"),
                explain={"icf_stage": "evidence_generator", "provenance": rec.get("provenance")},
            )
            out.append(
                {
                    "id": str(evidence.id),
                    "source": source_type,
                    "discovered_at": evidence.discovered_at.isoformat(),
                    "acquisition_method": evidence.acquisition_method,
                    "content_hash": evidence.content_hash,
                    "version": "2.0",
                    "original_uri": evidence.original_uri,
                    "trust_level": evidence.trust_level,
                    "entity_type": et,
                    "entity_value": ev,
                    "tenant_id": str(tenant_id),
                    "case_ref": case_ref,
                }
            )
        return out


_generator: EvidenceGenerator | None = None


def get_evidence_generator() -> EvidenceGenerator:
    global _generator
    if _generator is None:
        _generator = EvidenceGenerator()
    return _generator
