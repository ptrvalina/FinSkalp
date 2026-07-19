"""Normalize Fusion seed addresses (person:/org:/user:) into searchable queries."""

from __future__ import annotations

import re

_PREFIXES = ("person:", "org:", "organization:", "user:", "username:", "seed:")

_CYR_TO_LAT: dict[str, str] = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "shch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}

_WALLET_RE = re.compile(
    r"^(T[1-9A-HJ-NP-Za-km-z]{25,}|0x[a-fA-F0-9]{40}|bc1[a-z0-9]{25,}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})$"
)


def bare_seed_query(address: str) -> str:
    """Strip Fusion prefixes so collectors query the real name/org/handle."""
    raw = (address or "").strip()
    lower = raw.lower()
    for prefix in _PREFIXES:
        if lower.startswith(prefix):
            return raw[len(prefix) :].strip()
    return raw


def seed_kind(address: str) -> str:
    """Return wallet | person | org | user | unknown."""
    lower = (address or "").strip().lower()
    if lower.startswith("person:"):
        return "person"
    if lower.startswith("org:") or lower.startswith("organization:"):
        return "org"
    if lower.startswith("user:") or lower.startswith("username:"):
        return "user"
    bare = bare_seed_query(address)
    if _WALLET_RE.match(bare):
        return "wallet"
    return "unknown"


def is_named_seed(address: str) -> bool:
    return seed_kind(address) in {"person", "org", "user"}


def transliterate_cyrillic(value: str) -> str:
    out: list[str] = []
    for ch in value.lower():
        out.append(_CYR_TO_LAT.get(ch, ch))
    return "".join(out)


def person_to_usernames(full_name: str) -> list[str]:
    """
    RU ФИО → Latin Maigret handles.
    Order: Фамилия [Имя [Отчество]] (spaces are split, never passed to Maigret).
    """
    bare = bare_seed_query(full_name)
    parts = [p for p in re.split(r"\s+", bare.strip()) if p]
    if not parts:
        return []

    latin = [re.sub(r"[^a-z0-9._-]", "", transliterate_cyrillic(p)) for p in parts]
    latin = [p for p in latin if len(p) >= 2]
    if not latin:
        return []

    out: list[str] = []
    seen: set[str] = set()

    def add(token: str) -> None:
        t = token.strip("._-")
        if len(t) < 2 or t in seen:
            return
        seen.add(t)
        out.append(t)

    if len(latin) == 1:
        add(latin[0])
        return out[:6]

    # RU: surname, given, [patronymic]
    surname, given = latin[0], latin[1]
    add(surname)
    add(f"{surname}_{given}")
    add(f"{given}_{surname}")
    add(f"{given}{surname}")
    add(f"{surname}{given}")
    if given:
        add(f"{given[0]}{surname}")
        add(f"{surname}{given[0]}")
    return out[:6]
