"""RFC-0018 Ch.9 — graph narratives assistant."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.eia.explanation_engine import explain_graph_cluster, explain_links


def build_graph_narrative(
    *,
    entity_keys: list[str],
    context: dict[str, Any],
) -> dict[str, Any]:
    """Generate graph narrative for investigation entities."""
    if len(entity_keys) == 1:
        result = explain_links(entity_key=entity_keys[0], context=context)
    else:
        result = explain_graph_cluster(entity_keys=entity_keys, context=context)

    neighbors_total = sum(
        len((context.get("neighbors") or {}).get(k) or []) for k in entity_keys
    )

    narrative = result["narrative_ru"]
    if neighbors_total > 0:
        narrative += f" Всего связей в контексте: {neighbors_total}."

    return {
        **result,
        "narrative_ru": narrative,
        "entity_keys": entity_keys,
        "neighbor_count": neighbors_total,
    }
