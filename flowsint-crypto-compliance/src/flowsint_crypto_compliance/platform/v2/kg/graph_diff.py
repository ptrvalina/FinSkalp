"""Knowledge graph snapshot diff (RFC-0003 Ch.6, additive)."""

from __future__ import annotations

from typing import Any


def _entity_key(entity: dict[str, Any]) -> str:
    return str(entity.get("id") or entity.get("canonical_key") or "")


def _relation_key(relation: dict[str, Any]) -> str:
    return str(relation.get("id") or "")


def diff_graph_snapshots(graph_a: dict[str, Any], graph_b: dict[str, Any]) -> dict[str, Any]:
    """Compare two graph payloads (snapshot or reconstructed)."""
    entities_a = {_entity_key(e): e for e in graph_a.get("entities") or [] if _entity_key(e)}
    entities_b = {_entity_key(e): e for e in graph_b.get("entities") or [] if _entity_key(e)}
    relations_a = {_relation_key(r): r for r in graph_a.get("relations") or [] if _relation_key(r)}
    relations_b = {_relation_key(r): r for r in graph_b.get("relations") or [] if _relation_key(r)}

    added_entities = [entities_b[k] for k in entities_b if k not in entities_a]
    removed_entities = [entities_a[k] for k in entities_a if k not in entities_b]
    changed_entities: list[dict[str, Any]] = []
    for key in entities_a:
        if key in entities_b and entities_a[key] != entities_b[key]:
            changed_entities.append(
                {
                    "entity_id": key,
                    "from_version": entities_a[key].get("version"),
                    "to_version": entities_b[key].get("version"),
                    "display_name_from": entities_a[key].get("display_name"),
                    "display_name_to": entities_b[key].get("display_name"),
                }
            )

    added_relations = [relations_b[k] for k in relations_b if k not in relations_a]
    removed_relations = [relations_a[k] for k in relations_a if k not in relations_b]
    changed_relations: list[dict[str, Any]] = []
    for key in relations_a:
        if key in relations_b:
            conf_a = relations_a[key].get("confidence")
            conf_b = relations_b[key].get("confidence")
            if conf_a != conf_b or relations_a[key] != relations_b[key]:
                changed_relations.append(
                    {
                        "relation_id": key,
                        "confidence_from": conf_a,
                        "confidence_to": conf_b,
                        "relation_type": relations_b[key].get("relation_type"),
                    }
                )

    return {
        "ok": True,
        "as_of_a": graph_a.get("as_of"),
        "as_of_b": graph_b.get("as_of"),
        "entity_diff": {
            "added": len(added_entities),
            "removed": len(removed_entities),
            "changed": len(changed_entities),
            "added_samples": added_entities[:20],
            "removed_samples": removed_entities[:20],
            "changed_samples": changed_entities[:20],
        },
        "relation_diff": {
            "added": len(added_relations),
            "removed": len(removed_relations),
            "changed": len(changed_relations),
            "added_samples": added_relations[:20],
            "removed_samples": removed_relations[:20],
            "changed_samples": changed_relations[:20],
        },
        "summary": {
            "net_entities": len(entities_b) - len(entities_a),
            "net_relations": len(relations_b) - len(relations_a),
        },
    }
