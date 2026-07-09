"""In-memory store for imported KYT exposure rows (MetaSleuth / BlockSec)."""

from __future__ import annotations

from typing import Any

_store: dict[str, list[dict[str, Any]]] = {}


def _key(chain: str, address: str) -> str:
    return f"{chain.lower()}:{address}"


def put_exposure(chain: str, address: str, rows: list[dict[str, Any]]) -> int:
    key = _key(chain, address)
    existing = _store.get(key, [])
    merged = {r.get("entity_name", i): r for i, r in enumerate(existing)}
    for row in rows:
        merged[row.get("entity_name") or f"row_{len(merged)}"] = row
    _store[key] = list(merged.values())
    return len(_store[key])


def get_exposure(chain: str, address: str) -> list[dict[str, Any]]:
    return list(_store.get(_key(chain, address), []))


def clear_exposure(chain: str | None = None, address: str | None = None) -> None:
    if chain and address:
        _store.pop(_key(chain, address), None)
        return
    _store.clear()
