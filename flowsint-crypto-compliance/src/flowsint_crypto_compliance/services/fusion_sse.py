"""Shared SSE generator for compliance OSINT fusion progress."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any, Awaitable, Callable
from uuid import UUID

from flowsint_crypto_compliance.services.fusion_progress import FUSION_STEPS


async def fusion_sse_events(
    *,
    case_ref: str,
    request_is_disconnected: Callable[[], Awaitable[bool]],
    run_fusion: Callable[[], Awaitable[dict[str, Any]]],
) -> AsyncIterator[dict[str, str]]:
    try:
        yield {
            "event": "connected",
            "data": json.dumps({"case_ref": case_ref}, ensure_ascii=False),
        }
        for step_id, label_ru in FUSION_STEPS:
            if await request_is_disconnected():
                break
            yield {
                "event": "progress",
                "data": json.dumps(
                    {"step": step_id, "label_ru": label_ru, "status": "running"},
                    ensure_ascii=False,
                ),
            }
            await asyncio.sleep(0.04)

        result = await run_fusion()

        for step_id, label_ru in FUSION_STEPS:
            yield {
                "event": "progress",
                "data": json.dumps(
                    {"step": step_id, "label_ru": label_ru, "status": "done"},
                    ensure_ascii=False,
                ),
            }

        yield {
            "event": "complete",
            "data": json.dumps(
                {
                    "case_ref": result.get("case_ref"),
                    "graph_stats": result.get("graph_stats"),
                    "neo4j_export": result.get("neo4j_export"),
                    "neo4j_pivots": result.get("neo4j_pivots"),
                },
                ensure_ascii=False,
            ),
        }
    except asyncio.CancelledError:
        return
