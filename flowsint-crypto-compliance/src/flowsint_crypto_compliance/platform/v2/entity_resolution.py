"""Entity Resolution Engine — merge signals into canonical Entity (RFC-0002 M2, RFC-0003 Ch.7)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from flowsint_crypto_compliance.platform.v2.canonical import Entity, EntityAttribute, EntityType, normalize_entity_type


class MatchSignal(str, Enum):
    """Weighted match signals for entity resolution scoring."""

    IDENTIFIER = "identifier"
    ADDRESS = "address"
    PHONE = "phone"
    EMAIL = "email"
    NAME = "name"
    CRYPTO = "crypto"
    DOCUMENT = "document"
    DEVICE = "device"
    TEMPORAL = "temporal"
    GEO = "geo"
    BEHAVIORAL = "behavioral"


SIGNAL_WEIGHTS: dict[MatchSignal, float] = {
    MatchSignal.IDENTIFIER: 0.95,
    MatchSignal.CRYPTO: 0.92,
    MatchSignal.DOCUMENT: 0.90,
    MatchSignal.EMAIL: 0.85,
    MatchSignal.PHONE: 0.82,
    MatchSignal.ADDRESS: 0.78,
    MatchSignal.DEVICE: 0.75,
    MatchSignal.NAME: 0.55,
    MatchSignal.TEMPORAL: 0.45,
    MatchSignal.GEO: 0.40,
    MatchSignal.BEHAVIORAL: 0.35,
}


class MergeDecision(str, Enum):
    CREATE = "create"
    MERGE = "merge"
    LINK = "link"
    REJECT = "reject"


@dataclass
class ScoredCandidate:
    entity: Entity
    score: float
    signals: list[MatchSignal] = field(default_factory=list)
    explain: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResolutionResult:
    entity: Entity
    decision: MergeDecision
    confidence: float
    explain: dict[str, Any] = field(default_factory=dict)
    candidates: list[ScoredCandidate] = field(default_factory=list)


_SIGNAL_TO_ENTITY: dict[str, EntityType] = {
    "crypto_address": EntityType.WALLET,
    "blockchain_address": EntityType.BLOCKCHAIN_ADDRESS,
    "wallet": EntityType.WALLET,
    "tron": EntityType.WALLET,
    "eth": EntityType.WALLET,
    "btc": EntityType.WALLET,
    "phone": EntityType.PHONE,
    "email": EntityType.EMAIL,
    "domain": EntityType.DOMAIN,
    "dns_domain": EntityType.DNS_DOMAIN,
    "onion": EntityType.DOMAIN,
    "username": EntityType.USERNAME,
    "nickname": EntityType.NICKNAME,
    "alias": EntityType.ALIAS,
    "person": EntityType.PERSON,
    "organization": EntityType.ORGANIZATION,
    "company": EntityType.COMPANY,
    "case": EntityType.CASE,
    "ip_address": EntityType.IP_ADDRESS,
    "ip": EntityType.IP_ADDRESS,
    "passport": EntityType.PASSPORT,
    "telegram": EntityType.TELEGRAM,
    "forum": EntityType.FORUM,
}


def normalize_signal(entity_type: str, value: str) -> tuple[str, str]:
    et = entity_type.strip().lower()
    v = value.strip()
    if et == "username":
        v = v.lstrip("@").lower()
    elif et in ("domain", "onion", "dns_domain"):
        v = v.lower().removeprefix("http://").removeprefix("https://").split("/")[0]
    elif et == "email":
        v = v.lower()
    elif et == "phone":
        v = "".join(c for c in v if c.isdigit())[-10:]
    elif et in ("crypto_address", "wallet", "blockchain_address"):
        v = v.strip()
        if ":" not in v and len(v) > 20:
            v = f"unknown:{v}"
    return et, v


def canonical_key_for(entity_type: EntityType, normalized_value: str, *, chain: str | None = None) -> str:
    if entity_type in (EntityType.WALLET, EntityType.BLOCKCHAIN_ADDRESS):
        if ":" in normalized_value:
            return normalized_value
        chain_part = (chain or "unknown").lower()
        return f"{chain_part}:{normalized_value}"
    if entity_type == EntityType.CASE:
        return f"case:{normalized_value}"
    return f"{entity_type.value}:{normalized_value}"


def _signal_for_entity_type(raw_et: str) -> MatchSignal:
    mapping = {
        "crypto_address": MatchSignal.CRYPTO,
        "blockchain_address": MatchSignal.CRYPTO,
        "wallet": MatchSignal.CRYPTO,
        "phone": MatchSignal.PHONE,
        "email": MatchSignal.EMAIL,
        "domain": MatchSignal.ADDRESS,
        "dns_domain": MatchSignal.ADDRESS,
        "onion": MatchSignal.ADDRESS,
        "username": MatchSignal.NAME,
        "nickname": MatchSignal.NAME,
        "alias": MatchSignal.NAME,
        "person": MatchSignal.NAME,
        "passport": MatchSignal.DOCUMENT,
        "ip_address": MatchSignal.DEVICE,
        "ip": MatchSignal.DEVICE,
    }
    return mapping.get(raw_et, MatchSignal.IDENTIFIER)


class EntityResolutionEngine:
    """Merge wallet/phone/domain/email signals into canonical Entity records."""

    def resolve_signal(
        self,
        *,
        tenant_id: uuid.UUID,
        entity_type: str,
        value: str,
        chain: str | None = None,
        source: str = "entity_resolution",
        confidence: float = 0.5,
        display_name: str | None = None,
    ) -> Entity:
        raw_et, normalized = normalize_signal(entity_type, value)
        mapped = _SIGNAL_TO_ENTITY.get(raw_et)
        if mapped is None:
            mapped = normalize_entity_type(raw_et)
        chain_key = chain
        if raw_et in ("crypto_address", "wallet", "blockchain_address") and ":" in normalized:
            parts = normalized.split(":", 1)
            chain_key = parts[0]
            normalized = parts[1]
        key = canonical_key_for(mapped, normalized, chain=chain_key)
        name = display_name or normalized[:80]
        return Entity(
            tenant_id=tenant_id,
            entity_type=mapped,
            canonical_key=key,
            display_name=name,
            attributes=[
                EntityAttribute(
                    key="signal_type",
                    value=raw_et,
                    source=source,
                    confidence=confidence,
                ),
                EntityAttribute(
                    key="normalized_value",
                    value=normalized,
                    source=source,
                    confidence=confidence,
                ),
            ],
        )

    def find_candidates(
        self,
        *,
        tenant_id: uuid.UUID,
        entity_type: str,
        value: str,
        chain: str | None = None,
        store: Any | None = None,
    ) -> list[Entity]:
        """Find existing entities that might match the incoming signal."""
        ent = self.resolve_signal(
            tenant_id=tenant_id,
            entity_type=entity_type,
            value=value,
            chain=chain,
        )
        candidates: list[Entity] = []
        if store and hasattr(store, "get_entity_by_key"):
            existing = store.get_entity_by_key(
                tenant_id=tenant_id,
                entity_type=ent.entity_type.value,
                canonical_key=ent.canonical_key,
            )
            if existing:
                candidates.append(existing)
        if store and hasattr(store, "search_entities_by_value"):
            for hit in store.search_entities_by_value(tenant_id, value):
                if hit.id != ent.id and hit not in candidates:
                    candidates.append(hit)
        return candidates

    def score_match(
        self,
        candidate: Entity,
        *,
        entity_type: str,
        value: str,
        chain: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> ScoredCandidate:
        raw_et, normalized = normalize_signal(entity_type, value)
        signal = _signal_for_entity_type(raw_et)
        base_weight = SIGNAL_WEIGHTS.get(signal, 0.5)

        score = base_weight
        matched_signals = [signal]
        explain: dict[str, Any] = {"primary_signal": signal.value, "base_weight": base_weight}

        if context:
            if context.get("timestamp") is not None:
                w = SIGNAL_WEIGHTS[MatchSignal.TEMPORAL]
                score = min(1.0, score + w * 0.12)
                matched_signals.append(MatchSignal.TEMPORAL)
                explain["temporal_context"] = context["timestamp"]
            if context.get("geo") is not None:
                w = SIGNAL_WEIGHTS[MatchSignal.GEO]
                score = min(1.0, score + w * 0.12)
                matched_signals.append(MatchSignal.GEO)
                explain["geo_context"] = context["geo"]
            if context.get("behavior") is not None:
                w = SIGNAL_WEIGHTS[MatchSignal.BEHAVIORAL]
                score = min(1.0, score + w * 0.12)
                matched_signals.append(MatchSignal.BEHAVIORAL)
                explain["behavior_context"] = context["behavior"]

        cand_norm = next((a.value for a in candidate.attributes if a.key == "normalized_value"), None)
        if cand_norm and str(cand_norm) == normalized:
            score = min(1.0, score + 0.08)
            explain["exact_normalized_match"] = True

        if candidate.canonical_key.endswith(normalized) or normalized in candidate.canonical_key:
            score = min(1.0, score + 0.05)
            explain["canonical_key_overlap"] = True

        if candidate.entity_type == normalize_entity_type(raw_et):
            score = min(1.0, score + 0.03)
            explain["type_match"] = True

        return ScoredCandidate(
            entity=candidate,
            score=round(score, 4),
            signals=matched_signals,
            explain=explain,
        )

    def resolve_with_scoring(
        self,
        *,
        tenant_id: uuid.UUID,
        entity_type: str,
        value: str,
        chain: str | None = None,
        source: str = "entity_resolution",
        confidence: float = 0.5,
        display_name: str | None = None,
        store: Any | None = None,
        merge_threshold: float = 0.85,
        context: dict[str, Any] | None = None,
    ) -> ResolutionResult:
        """Return merge decision + confidence + explain."""
        proposed = self.resolve_signal(
            tenant_id=tenant_id,
            entity_type=entity_type,
            value=value,
            chain=chain,
            source=source,
            confidence=confidence,
            display_name=display_name,
        )
        candidates = self.find_candidates(
            tenant_id=tenant_id,
            entity_type=entity_type,
            value=value,
            chain=chain,
            store=store,
        )
        scored = [
            self.score_match(
                c,
                entity_type=entity_type,
                value=value,
                chain=chain,
                context=context,
            )
            for c in candidates
        ]
        scored.sort(key=lambda s: s.score, reverse=True)

        if scored and scored[0].score >= merge_threshold:
            primary = scored[0].entity
            merged = self.merge_entities(primary, [proposed])
            return ResolutionResult(
                entity=merged,
                decision=MergeDecision.MERGE,
                confidence=scored[0].score,
                explain={
                    "decision": "merge",
                    "matched_entity_id": str(primary.id),
                    **scored[0].explain,
                },
                candidates=scored,
            )

        if scored and scored[0].score >= 0.65:
            return ResolutionResult(
                entity=proposed,
                decision=MergeDecision.LINK,
                confidence=scored[0].score,
                explain={
                    "decision": "link",
                    "related_entity_id": str(scored[0].entity.id),
                    **scored[0].explain,
                },
                candidates=scored,
            )

        signal = _signal_for_entity_type(entity_type)
        return ResolutionResult(
            entity=proposed,
            decision=MergeDecision.CREATE,
            confidence=min(1.0, confidence * SIGNAL_WEIGHTS.get(signal, 0.5)),
            explain={
                "decision": "create",
                "signal": signal.value,
                "weight": SIGNAL_WEIGHTS.get(signal, 0.5),
            },
            candidates=scored,
        )

    def merge_signals(
        self,
        signals: list[tuple[str, str]],
        *,
        tenant_id: uuid.UUID,
        chain: str | None = None,
        source: str = "entity_resolution",
    ) -> list[Entity]:
        seen: set[str] = set()
        out: list[Entity] = []
        for et, val in signals:
            ent = self.resolve_signal(
                tenant_id=tenant_id,
                entity_type=et,
                value=val,
                chain=chain,
                source=source,
            )
            if ent.canonical_key in seen:
                continue
            seen.add(ent.canonical_key)
            out.append(ent)
        return out

    def merge_entities(self, primary: Entity, others: list[Entity]) -> Entity:
        """Return primary with merged attributes from duplicates."""
        merged_ids = [str(o.id) for o in others]
        attrs = list(primary.attributes)
        for other in others:
            for attr in other.attributes:
                if not any(a.key == attr.key and a.value == attr.value for a in attrs):
                    attrs.append(attr)
        return primary.model_copy(
            update={
                "attributes": attrs,
                "version": primary.version + 1,
            }
        ).with_attribute(
            EntityAttribute(
                key="merged_ids",
                value=merged_ids,
                source="entity_resolution",
                confidence=1.0,
            )
        )

    def payload_to_signals(self, payload: dict[str, Any]) -> list[tuple[str, str]]:
        """Extract resolvable signals from fusion/OSINT payload."""
        signals: list[tuple[str, str]] = []
        for key in ("address", "wallet", "phone", "email", "domain"):
            val = payload.get(key)
            if val:
                signals.append((key, str(val)))
        chain = payload.get("chain")
        if chain and payload.get("address"):
            signals.append(("crypto_address", f"{str(chain).lower()}:{payload['address']}"))
        for m in payload.get("mentions") or []:
            if not isinstance(m, dict):
                continue
            for k in ("phone", "email", "domain", "username"):
                if m.get(k):
                    signals.append((k, str(m[k])))
        return signals
