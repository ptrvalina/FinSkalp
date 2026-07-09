from __future__ import annotations

from dataclasses import dataclass

from flowsint_types.fiat_crypto import EntityKind, EvidenceSource

# Source priority for conflict resolution (higher wins on entity/region disputes)
SOURCE_PRIORITY: dict[EvidenceSource, float] = {
    EvidenceSource.CONTROL_PURCHASE: 1.0,
    EvidenceSource.BANK_REGULATOR_HUB: 0.95,
    EvidenceSource.FIU_ALERT: 0.93,
    EvidenceSource.BANK_ALERT: 0.92,
    EvidenceSource.SOVEREIGN_REGISTRY: 0.9,
    EvidenceSource.LICENSED_PLATFORM: 0.9,
    EvidenceSource.BLOCKCHAIN: 0.7,
    EvidenceSource.OSINT: 0.65,
}

CIS_DOMESTIC_REGIONS = frozenset(
    {"RU", "BY", "KZ", "KG", "UZ", "TJ", "AM", "AZ", "MD", "GE"}
)


@dataclass
class MergeDecision:
    sovereign_label: str | None
    watchlist_label: str | None
    label_source: str | None
    sanctioned: bool
    list_reference: str | None
    entity_kind: EntityKind
    disputed: bool
    confidence: float
    evidence_chain: list[str]


class MergeEngine:
    """
    Merge on-chain sovereign attribution with the sovereign RF/CIS risk registry.

    Rules:
      1. Domestic/regulator evidence always wins on RU/CIS region conflicts
      2. Registry hit supplements entity name when domestic attribution is unknown
      3. Disputed registry labels never override the domestic attribution
      4. Control purchase = ground truth for wallet role
      5. A 115-FZ / sanctions list hit is authoritative and forces a high score
    """

    def merge(
        self,
        *,
        address: str,
        sovereign_label: str | None,
        sovereign_confidence: float,
        sovereign_region: str | None,
        sovereign_kind: EntityKind,
        sovereign_evidence: list[str],
        registry_entity: str | None,
        registry_source: str | None,
        registry_confidence: float,
        registry_disputed: bool,
        registry_category: str | None,
        registry_sanctioned: bool = False,
        registry_list_reference: str | None = None,
        linkage_strength: float,
        bank_linked: bool,
    ) -> MergeDecision:
        evidence = list(sovereign_evidence)
        confidence = sovereign_confidence
        entity_kind = sovereign_kind
        disputed = registry_disputed

        watchlist_label = registry_entity
        if registry_source and registry_entity:
            evidence.append(f"registry:{registry_source}:{registry_entity}")

        # Boost confidence when bank directly linked
        if bank_linked:
            confidence = min(1.0, confidence + linkage_strength * 0.25)
            evidence.append(f"bank_linkage:{linkage_strength:.2f}")

        # Registry supplements unknown sovereign entity
        if not sovereign_label and registry_entity and not registry_disputed:
            confidence = min(
                1.0,
                confidence
                + registry_confidence * SOURCE_PRIORITY[EvidenceSource.SOVEREIGN_REGISTRY],
            )
            entity_kind = _category_to_kind(registry_category) or entity_kind
            evidence.append("merge:registry_supplement")

        # Sovereign wins on CIS domestic region
        if sovereign_region and sovereign_region.upper() in CIS_DOMESTIC_REGIONS:
            if registry_disputed:
                evidence.append("merge:domestic_wins_disputed_registry")
            else:
                evidence.append(f"merge:domestic_region_anchor:{sovereign_region}")

        # Both agree → confidence boost
        if (
            sovereign_label
            and registry_entity
            and not registry_disputed
            and _labels_compatible(sovereign_label, registry_entity)
        ):
            confidence = min(1.0, confidence + 0.12)
            evidence.append("merge:sovereign_registry_agreement")

        # Sanctions / 115-FZ list hit is authoritative
        if registry_sanctioned:
            confidence = max(confidence, 0.96)
            ref = registry_list_reference or "115-ФЗ"
            evidence.append(f"registry:sanctioned:{ref}")

        return MergeDecision(
            sovereign_label=sovereign_label,
            watchlist_label=watchlist_label,
            label_source=registry_source,
            sanctioned=registry_sanctioned,
            list_reference=registry_list_reference,
            entity_kind=entity_kind,
            disputed=disputed,
            confidence=round(min(1.0, confidence), 3),
            evidence_chain=evidence,
        )


def _category_to_kind(category: str | None) -> EntityKind | None:
    if not category:
        return None
    c = category.lower()
    if "exchange" in c or "cex" in c:
        return EntityKind.CEX
    if "mixer" in c:
        return EntityKind.MIXER
    if "bridge" in c:
        return EntityKind.BRIDGE
    if "otc" in c or "p2p" in c:
        return EntityKind.OTC
    return None


def _labels_compatible(sovereign: str, registry: str) -> bool:
    s = sovereign.lower()
    i = registry.lower()
    return s in i or i in s or s.split("_")[0] in i
