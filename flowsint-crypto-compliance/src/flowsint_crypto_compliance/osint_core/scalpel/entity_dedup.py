"""Fuzzy dedup сущностей (VASP, имена) через RapidFuzz."""

from __future__ import annotations

from typing import Any


def merge_entity_names(names: list[str], *, threshold: int = 88) -> list[str]:
    if not names:
        return []
    try:
        from rapidfuzz import fuzz
    except ImportError:
        return list(dict.fromkeys(n.strip() for n in names if n.strip()))

    unique: list[str] = []
    for name in names:
        n = name.strip()
        if not n:
            continue
        if any(fuzz.ratio(n.lower(), u.lower()) >= threshold for u in unique):
            continue
        unique.append(n)
    return unique


def dedupe_mentions_by_excerpt(mentions: list[Any], *, threshold: int = 90) -> list[Any]:
    if len(mentions) < 2:
        return mentions
    try:
        from rapidfuzz import fuzz
    except ImportError:
        return mentions

    out: list[Any] = []
    for m in mentions:
        excerpt = (getattr(m, "excerpt_ru", None) or "")[:80]
        if any(
            fuzz.ratio(excerpt, (getattr(o, "excerpt_ru", None) or "")[:80]) >= threshold
            for o in out
        ):
            continue
        out.append(m)
    return out
