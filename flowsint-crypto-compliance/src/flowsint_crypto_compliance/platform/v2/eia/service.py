"""RFC-0018 EIA service facade."""

from __future__ import annotations

import uuid
from typing import Any

from flowsint_crypto_compliance.platform.v2.eia.context_engine import build_investigation_context
from flowsint_crypto_compliance.platform.v2.eia.manifest import eia_manifest
from flowsint_crypto_compliance.platform.v2.eia.monitoring import get_eia_metrics
from flowsint_crypto_compliance.platform.v2.eia.orchestrator import run_eia_task
from flowsint_crypto_compliance.platform.v2.eia.prompt_registry import list_all_prompts, list_prompt_versions


class EIAService:
    """Explainable AI & Investigation Assistant service."""

    def manifest(self) -> dict[str, Any]:
        return eia_manifest()

    async def assist(
        self,
        *,
        task_type: str,
        case_ref: str,
        entity_keys: list[str] | None = None,
        tenant_id: uuid.UUID | None = None,
        actor: str = "eia.api",
        prompt_version: str | None = None,
    ) -> dict[str, Any]:
        result = await run_eia_task(
            task_type=task_type,
            case_ref=case_ref,
            entity_keys=entity_keys,
            tenant_id=tenant_id,
            actor=actor,
            prompt_version=prompt_version,
        )
        return result.to_dict()

    async def get_context(
        self,
        *,
        case_ref: str,
        entity_keys: list[str] | None = None,
        tenant_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        return await build_investigation_context(
            case_ref=case_ref,
            entity_keys=entity_keys or [],
            tenant_id=tenant_id,
        )

    def get_prompts(self, task_type: str | None = None) -> dict[str, Any]:
        if task_type:
            versions = list_prompt_versions(task_type)
            return {"ok": True, "task_type": task_type, "versions": versions}
        return {"ok": True, "prompts": list_all_prompts()}

    def monitoring(self) -> dict[str, Any]:
        return {"ok": True, **get_eia_metrics().get_metrics()}


_service: EIAService | None = None


def get_eia_service() -> EIAService:
    global _service
    if _service is None:
        _service = EIAService()
    return _service
