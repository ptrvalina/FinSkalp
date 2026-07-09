"""RFC-0014 Ch.6 — entity extraction with provenance."""

from __future__ import annotations

import json
from typing import Any

from flowsint_crypto_compliance.osint_core.scalpel.entity_extractor import extract_entities


def _entity_record(
    *,
    entity_type: str,
    entity_value: str,
    source_id: str,
    provenance: dict[str, Any],
    confidence: float = 0.6,
) -> dict[str, Any]:
    return {
        "entity_type": entity_type,
        "entity_value": entity_value,
        "source_type": source_id,
        "confidence": confidence,
        "provenance": provenance,
        "payload": {"extracted": True, **provenance},
    }


class ICFEntityExtractor:
    """Port scalpel extract_entities — canonical entity records with provenance."""

    def extract_from_records(
        self,
        records: list[dict[str, Any]],
        *,
        connector_id: str,
        provenance_base: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        base = dict(provenance_base or {})
        base.setdefault("connector_id", connector_id)
        base.setdefault("extraction_method", "scalpel.extract_entities")

        out: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()

        for rec in records:
            prov = {**base, "source_record": rec.get("entity_value") or rec.get("entity_type")}
            text_parts = [
                str(rec.get("entity_value") or ""),
                json.dumps(rec.get("payload") or {}, ensure_ascii=False) if rec.get("payload") else "",
            ]
            text = " ".join(p for p in text_parts if p).strip()
            if not text:
                continue

            extracted = extract_entities(text, context_address=str(rec.get("entity_value") or ""))
            for item in extracted.crypto_addresses:
                key = ("crypto_address", item["address"])
                if key not in seen:
                    seen.add(key)
                    out.append(
                        _entity_record(
                            entity_type="crypto_address",
                            entity_value=item["address"],
                            source_id=connector_id,
                            provenance={**prov, "chain": item.get("chain")},
                            confidence=float(rec.get("confidence") or 0.7),
                        )
                    )
            for inn in extracted.inn:
                key = ("organization", inn)
                if key not in seen:
                    seen.add(key)
                    out.append(
                        _entity_record(
                            entity_type="organization",
                            entity_value=inn,
                            source_id=connector_id,
                            provenance={**prov, "identifier_type": "inn"},
                        )
                    )
            for ogrn in extracted.ogrn:
                key = ("organization", ogrn)
                if key not in seen:
                    seen.add(key)
                    out.append(
                        _entity_record(
                            entity_type="organization",
                            entity_value=ogrn,
                            source_id=connector_id,
                            provenance={**prov, "identifier_type": "ogrn"},
                        )
                    )
            for phone in extracted.phones:
                key = ("phone", phone)
                if key not in seen:
                    seen.add(key)
                    out.append(
                        _entity_record(
                            entity_type="phone",
                            entity_value=phone,
                            source_id=connector_id,
                            provenance=prov,
                        )
                    )
            for email in extracted.emails:
                key = ("email", email)
                if key not in seen:
                    seen.add(key)
                    out.append(
                        _entity_record(
                            entity_type="email",
                            entity_value=email,
                            source_id=connector_id,
                            provenance=prov,
                        )
                    )
            for domain in extracted.domains:
                key = ("domain", domain)
                if key not in seen:
                    seen.add(key)
                    out.append(
                        _entity_record(
                            entity_type="domain",
                            entity_value=domain,
                            source_id=connector_id,
                            provenance=prov,
                        )
                    )
            for username in extracted.usernames:
                key = ("username", username)
                if key not in seen:
                    seen.add(key)
                    out.append(
                        _entity_record(
                            entity_type="username",
                            entity_value=username,
                            source_id=connector_id,
                            provenance=prov,
                        )
                    )

        return out


_extractor: ICFEntityExtractor | None = None


def get_entity_extractor() -> ICFEntityExtractor:
    global _extractor
    if _extractor is None:
        _extractor = ICFEntityExtractor()
    return _extractor
