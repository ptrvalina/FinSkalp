"""RFC-0014 Ch.9 — fusion integration bridge."""

from __future__ import annotations

import uuid
from typing import Any

from flowsint_crypto_compliance.platform.v2.fusion_pipeline import FusionPipeline


async def run_fusion_bridge(
    records: list[dict[str, Any]],
    *,
    tenant_id: uuid.UUID,
    case_ref: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Run fusion_pipeline with include_rfc0003=True — collector does not fuse."""
    pipeline = FusionPipeline.with_rfc0003_path()
    events = await pipeline.run(
        records,
        tenant_id=tenant_id,
        correlation_id=correlation_id or case_ref,
        context={"case_ref": case_ref, "source": "icf"},
        include_rfc0003=True,
    )
    return {
        "events_emitted": len(events),
        "stages": [e.payload.get("stage") for e in events if e.payload],
        "ok": bool(events),
    }
