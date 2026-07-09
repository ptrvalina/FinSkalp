"""RFC-0017 Ch.3 — evidence ID allocation EV-YYYY-NNNNNNNNNNNN."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock

_lock = Lock()
_counters: dict[int, int] = {}


def allocate_evidence_id(*, year: int | None = None) -> str:
    """Allocate next evidence ID: EV-YYYY-NNNNNNNNNNNN (12-digit sequence)."""
    y = year or datetime.now(timezone.utc).year
    with _lock:
        seq = _counters.get(y, 0) + 1
        _counters[y] = seq
    return f"EV-{y}-{seq:012d}"


def reset_id_counters() -> None:
    """Test helper — reset in-memory counters."""
    with _lock:
        _counters.clear()
