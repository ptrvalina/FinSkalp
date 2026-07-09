"""mTLS client for sovereign regulator bank hub (115-ФЗ)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

from flowsint_crypto_compliance.schemas.hub import validate_bank_feed_batch


@dataclass(frozen=True)
class RegulatorHubConfig:
    base_url: str
    hub_id: str = "fiu-hub-ru"
    client_cert: str | None = None
    client_key: str | None = None
    ca_bundle: str | None = None
    bearer_token: str | None = None
    timeout_s: float = 30.0

    @classmethod
    def from_env(cls) -> RegulatorHubConfig | None:
        base = os.getenv("REGULATOR_HUB_URL")
        if not base:
            return None
        return cls(
            base_url=base.rstrip("/"),
            hub_id=os.getenv("REGULATOR_HUB_ID", "fiu-hub-ru"),
            client_cert=os.getenv("REGULATOR_HUB_CLIENT_CERT"),
            client_key=os.getenv("REGULATOR_HUB_CLIENT_KEY"),
            ca_bundle=os.getenv("REGULATOR_HUB_CA_BUNDLE"),
            bearer_token=os.getenv("REGULATOR_HUB_TOKEN"),
        )


class RegulatorAPIConnector:
    """Pull bank STR batches from regulator hub over HTTPS + mTLS."""

    def __init__(self, config: RegulatorHubConfig) -> None:
        self._config = config

    def _client(self) -> httpx.Client:
        cert = None
        if self._config.client_cert and self._config.client_key:
            cert = (self._config.client_cert, self._config.client_key)
        verify = self._config.ca_bundle or True
        return httpx.Client(cert=cert, verify=verify, timeout=self._config.timeout_s)

    def fetch_bank_feed_batch(
        self,
        *,
        since: str | None = None,
        limit: int = 500,
    ) -> dict[str, Any]:
        headers: dict[str, str] = {}
        if self._config.bearer_token:
            headers["Authorization"] = f"Bearer {self._config.bearer_token}"

        params: dict[str, Any] = {"hub_id": self._config.hub_id, "limit": limit}
        if since:
            params["since"] = since

        with self._client() as client:
            response = client.get(
                f"{self._config.base_url}/v1/bank-feeds",
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()

        if "feeds" not in payload:
            payload = {
                "schema_version": "regulator-hub/v1",
                "hub_id": self._config.hub_id,
                "feeds": payload if isinstance(payload, list) else [],
            }
        payload.setdefault("schema_version", "regulator-hub/v1")
        payload.setdefault("hub_id", self._config.hub_id)
        validate_bank_feed_batch(payload)
        return payload

    @staticmethod
    def from_env() -> RegulatorAPIConnector | None:
        config = RegulatorHubConfig.from_env()
        return RegulatorAPIConnector(config) if config else None
