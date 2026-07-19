"""Gradual Entity typing (RFC-4 path) — additive bridge from entity_labels."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

EntityKind = Literal["wallet", "person", "organization", "transaction", "domain", "unknown"]


class EntityBase(TypedDict, total=False):
    """Minimal shared interface for new entity types without big-bang migration."""

    entity_id: str
    entity_type: EntityKind
    display_name: str
    chain: str | None
    address: str | None
    confidence: float
    risk_score: float | None
    sources: list[str]
    metadata: dict[str, Any]


def entity_from_label(
    *,
    chain: str,
    address: str,
    label: str,
    category: str | None = None,
    confidence: float = 0.5,
    risk_score: float | None = None,
    sources: list[str] | None = None,
) -> EntityBase:
    kind: EntityKind = "wallet"
    cat = (category or "").lower()
    if cat in ("person", "individual"):
        kind = "person"
    elif cat in ("company", "organization", "vasp", "exchange", "bank"):
        kind = "organization"
    return EntityBase(
        entity_id=f"{chain}:{address}",
        entity_type=kind,
        display_name=label or address,
        chain=chain,
        address=address,
        confidence=confidence,
        risk_score=risk_score,
        sources=sources or [],
        metadata={"category": category} if category else {},
    )
