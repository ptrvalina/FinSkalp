"""Unleash feature flags for risk-logic gradual rollout (self-hosted)."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FlagContext:
    user_id: str | None = None
    case_id: str | None = None
    owner_id: str | None = None
    properties: dict[str, str] = field(default_factory=dict)


class FeatureFlags:
    """Unleash client with env-based fallback when server unavailable."""

    RISK_FLAGS = (
        "finskalp.cospend_v2",
        "finskalp.illegal_flow_detector_v2",
        "finskalp.xgboost_scoring_v2",
        "finskalp.funnel_consolidation",
        "finskalp.attribution_eval_gate",
    )

    def __init__(self) -> None:
        self._client = None
        self._url = os.getenv("UNLEASH_URL", "http://localhost:4242/api")
        self._api_token = os.getenv("UNLEASH_API_TOKEN", "development.unleash-insecure-api-token")
        self._app_name = os.getenv("UNLEASH_APP_NAME", "finskalp-compliance")
        self._env_fallback = os.getenv("FINSKALP_FEATURE_FLAGS", "")
        self._init_client()

    def _init_client(self) -> None:
        if os.getenv("UNLEASH_DISABLED", "").lower() in ("1", "true", "yes"):
            self._client = None
            return
        if self._env_fallback and not os.getenv("UNLEASH_URL"):
            self._client = None
            return
        try:
            from UnleashClient import UnleashClient

            self._client = UnleashClient(
                url=self._url,
                app_name=self._app_name,
                custom_headers={"Authorization": self._api_token},
            )
            self._client.initialize_client()
        except Exception:
            self._client = None

    def is_enabled(self, flag: str, ctx: FlagContext | None = None) -> bool:
        enabled = self._is_enabled_raw(flag, ctx)
        if enabled and flag in self.RISK_FLAGS and flag != "finskalp.attribution_eval_gate":
            if self._is_enabled_raw("finskalp.attribution_eval_gate", ctx) and not rollout_allowed(flag, ctx):
                return False
        return enabled

    def _is_enabled_raw(self, flag: str, ctx: FlagContext | None = None) -> bool:
        if self._client:
            try:
                context = self._to_unleash_context(ctx)
                return bool(self._client.is_enabled(flag, context))
            except Exception:
                pass
        return self._env_fallback_enabled(flag, ctx)

    def _env_fallback_enabled(self, flag: str, ctx: FlagContext | None) -> bool:
        """FINSKALP_FEATURE_FLAGS=cospend_v2,funnel_consolidation or FINSKALP_FLAG_<NAME>=1"""
        env_key = f"FINSKALP_FLAG_{flag.split('.')[-1].upper()}"
        if os.getenv(env_key) == "1":
            return True
        if flag.split(".")[-1] in self._env_fallback.split(","):
            return True
        return False

    def rollout_bucket(self, ctx: FlagContext, salt: str = "") -> int:
        """Deterministic 0-99 bucket for % rollout without Unleash."""
        key = f"{ctx.user_id or ctx.owner_id or ctx.case_id or 'anon'}:{salt}"
        return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) % 100

    def is_enabled_pct(self, flag: str, pct: int, ctx: FlagContext | None = None) -> bool:
        if not self.is_enabled(flag, ctx):
            return False
        if pct >= 100:
            return True
        bucket = self.rollout_bucket(ctx or FlagContext(), salt=flag)
        return bucket < pct

    @staticmethod
    def _to_unleash_context(ctx: FlagContext | None) -> dict[str, Any]:
        if not ctx:
            return {}
        out: dict[str, Any] = {}
        if ctx.user_id:
            out["userId"] = ctx.user_id
        props = dict(ctx.properties)
        if ctx.case_id:
            props["caseId"] = ctx.case_id
        if ctx.owner_id:
            props["ownerId"] = ctx.owner_id
        if props:
            out["properties"] = props
        return out


_flags: FeatureFlags | None = None


def get_feature_flags() -> FeatureFlags:
    global _flags
    if _flags is None:
        _flags = FeatureFlags()
    return _flags


def rollout_allowed(flag: str, ctx: FlagContext | None = None) -> bool:
    """Block risk-flag rollout when eval gate is active and last report failed."""
    gate_env = os.getenv("FINSKALP_EVAL_GATE", "").lower()
    if gate_env == "pass":
        return True
    if gate_env == "block":
        return False
    try:
        import json
        from pathlib import Path

        report_dir = Path(os.getenv("FINSKALP_EVAL_REPORT_DIR", "reports/attribution_eval"))
        reports = sorted(report_dir.glob("eval_*.json"), reverse=True)
        if not reports:
            return True
        data = json.loads(reports[0].read_text(encoding="utf-8"))
        gate = data.get("deploy_gate") or {}
        return gate.get("passed", True)
    except Exception:
        return True
