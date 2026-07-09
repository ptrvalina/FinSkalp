"""RFC-0015 Ch.7 — sanctions screening with exact/fuzzy/transliteration matching."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any

# Minimal transliteration map RU → LAT
_CYR_TO_LAT: dict[str, str] = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}

_SANCTIONS_LIST: list[dict[str, Any]] = [
    {"name": "ACME SANCTIONS CORP", "list": "OFAC SDN", "program": "CYBER2"},
    {"name": "ROSNEFT OIL COMPANY", "list": "OFAC SDN", "program": "UKRAINE-EO13662"},
    {"name": "GAZPROM BANK", "list": "OFAC SDN", "program": "RUSSIA-EO14024"},
    {"name": "TEST ORGANIZATION", "list": "OFAC SDN", "program": "CYBER2"},
]


def _normalize_name(name: str) -> str:
    n = unicodedata.normalize("NFKD", name.upper().strip())
    n = re.sub(r"[^A-Z0-9\s]", "", n)
    return re.sub(r"\s+", " ", n)


def _transliterate(name: str) -> str:
    out = []
    for ch in name.lower():
        out.append(_CYR_TO_LAT.get(ch, ch))
    return "".join(out).upper()


def _fuzzy_score(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize_name(a), _normalize_name(b)).ratio()


def screen_sanctions(
    name: str,
    *,
    threshold: float = 0.85,
    fuzzy_threshold: float = 0.72,
) -> list[dict[str, Any]]:
    """
    Screen name against sanctions list.
    Probable (fuzzy/transliteration) matches always require analyst confirmation.
    """
    results: list[dict[str, Any]] = []
    norm_query = _normalize_name(name)
    translit_query = _normalize_name(_transliterate(name))

    for entry in _SANCTIONS_LIST:
        entry_name = entry["name"]
        norm_entry = _normalize_name(entry_name)

        if norm_query == norm_entry:
            results.append(
                {
                    "match_type": "exact",
                    "confidence": 1.0,
                    "requires_analyst_confirmation": False,
                    "matched_name": entry_name,
                    "query_name": name,
                    **entry,
                }
            )
            continue

        fuzzy = max(_fuzzy_score(name, entry_name), _fuzzy_score(translit_query, norm_entry))
        if fuzzy >= fuzzy_threshold:
            results.append(
                {
                    "match_type": "fuzzy" if fuzzy < threshold else "probable",
                    "confidence": round(fuzzy, 4),
                    "requires_analyst_confirmation": True,
                    "matched_name": entry_name,
                    "query_name": name,
                    **entry,
                }
            )
            continue

        if translit_query and _fuzzy_score(translit_query, norm_entry) >= fuzzy_threshold:
            results.append(
                {
                    "match_type": "transliteration",
                    "confidence": round(_fuzzy_score(translit_query, norm_entry), 4),
                    "requires_analyst_confirmation": True,
                    "matched_name": entry_name,
                    "query_name": name,
                    **entry,
                }
            )

    results.sort(key=lambda r: r["confidence"], reverse=True)
    return results
