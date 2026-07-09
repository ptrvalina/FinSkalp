"""Entity store mode — RFC-0003 production vs offline (Ch. storage policy)."""

from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger(__name__)


def entity_store_mode() -> str:
    """Resolve KG backend: postgres (default) or memory when explicitly set."""
    from flowsint_crypto_compliance.demo.combat_mode import resolve_entity_store_mode

    return resolve_entity_store_mode()


def is_memory_store_mode() -> bool:
    return entity_store_mode() in ("memory", "in_memory")


def warn_if_memory_store_in_production() -> None:
    """Log startup warning when KG runs in non-persistent memory mode."""
    if not is_memory_store_mode():
        return
    if os.getenv("PYTEST_CURRENT_TEST") or os.getenv("TESTING", "").strip() in ("1", "true"):
        return
    msg = (
        "ВНИМАНИЕ: FINSKALP_ENTITY_STORE=memory — граф знаний не персистентен. "
        "Для production задайте FINSKALP_ENTITY_STORE=postgres"
    )
    logger.warning(msg)
    print(msg, file=sys.stderr)
