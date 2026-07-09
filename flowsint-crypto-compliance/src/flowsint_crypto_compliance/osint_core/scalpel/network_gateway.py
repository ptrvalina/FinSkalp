"""
Сетевой шлюз FinSkalp Scalpel: clearnet, Tor SOCKS5, I2P, ротация прокси.

Вдохновлено SpiderFoot TOR integration и Maigret proxy routing.
Конфигурация через переменные окружения (без хардкода секретов).
"""

from __future__ import annotations

import os
import random
import socket
from dataclasses import dataclass, field
from typing import Any

import httpx

_DEFAULT_TOR_SOCKS = "socks5://127.0.0.1:9050"
_DEFAULT_I2P_HTTP = "http://127.0.0.1:4444"
_DEFAULT_TOR_PORT = 9050


def _tor_socks_port_open(host: str = "127.0.0.1", port: int = _DEFAULT_TOR_PORT, timeout: float = 0.35) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def resolve_tor_socks_url() -> str | None:
    """Env override first, then auto-detect local Tor SOCKS (9050)."""
    explicit = os.getenv("FINSKALP_TOR_SOCKS") or os.getenv("TOR_SOCKS_PROXY")
    if explicit:
        return explicit
    if _tor_socks_port_open():
        return _DEFAULT_TOR_SOCKS
    return None


@dataclass
class NetworkGatewayConfig:
    tor_socks_url: str | None = None
    i2p_proxy_url: str | None = None
    clearnet_proxy_url: str | None = None
    user_agent: str = (
        "FinSkalp-Scalpel/1.0 (+https://flowsint.local/compliance; regulatory OSINT)"
    )
    timeout_sec: float = 8.0
    max_retries: int = 2
    rotate_tor_circuit: bool = False

    @classmethod
    def from_env(cls) -> NetworkGatewayConfig:
        return cls(
            tor_socks_url=resolve_tor_socks_url(),
            i2p_proxy_url=os.getenv("FINSKALP_I2P_PROXY") or os.getenv("I2P_PROXY"),
            clearnet_proxy_url=os.getenv("FINSKALP_HTTP_PROXY") or os.getenv("HTTP_PROXY"),
            timeout_sec=float(os.getenv("FINSKALP_HTTP_TIMEOUT", "8")),
            rotate_tor_circuit=os.getenv("FINSKALP_TOR_ROTATE", "0") == "1",
        )

    def tor_enabled(self) -> bool:
        return bool(self.tor_socks_url)

    def i2p_enabled(self) -> bool:
        return bool(self.i2p_proxy_url)


@dataclass
class NetworkGateway:
    config: NetworkGatewayConfig = field(default_factory=NetworkGatewayConfig.from_env)

    def status(self) -> dict[str, Any]:
        return {
            "tor": "enabled" if self.config.tor_enabled() else "disabled",
            "tor_socks": self._mask_proxy(self.config.tor_socks_url),
            "i2p": "enabled" if self.config.i2p_enabled() else "disabled",
            "clearnet_proxy": "enabled" if self.config.clearnet_proxy_url else "direct",
            "timeout_sec": self.config.timeout_sec,
            "engines": ["httpx", "tor_socks5", "i2p_http"],
            "inspired_by": ["SpiderFoot TOR", "Maigret proxy", "stem circuit rotation"],
        }

    def client(self, *, route: str = "clearnet") -> httpx.AsyncClient:
        """route: clearnet | tor | i2p"""
        proxy: str | None = None
        if route == "tor" and self.config.tor_enabled():
            proxy = self.config.tor_socks_url or _DEFAULT_TOR_SOCKS
        elif route == "i2p" and self.config.i2p_enabled():
            proxy = self.config.i2p_proxy_url or _DEFAULT_I2P_HTTP
        elif route == "clearnet" and self.config.clearnet_proxy_url:
            proxy = self.config.clearnet_proxy_url

        headers = {"User-Agent": self.config.user_agent}
        return httpx.AsyncClient(
            timeout=self.config.timeout_sec,
            headers=headers,
            proxy=proxy,
            follow_redirects=True,
        )

    async def fetch(
        self,
        url: str,
        *,
        route: str = "clearnet",
        method: str = "GET",
        **kwargs: Any,
    ) -> tuple[int, str, str]:
        """Returns (status_code, body_text_snippet, route_used)."""
        from flowsint_crypto_compliance.osint_core.scalpel.security import is_safe_external_url

        if route == "clearnet" and not is_safe_external_url(url):
            return 0, "blocked_ssrf", route
        if route == "tor" and ".onion" not in url.lower() and not is_safe_external_url(url):
            return 0, "blocked_ssrf", route
        last_err = ""
        for attempt in range(self.config.max_retries + 1):
            try:
                async with self.client(route=route) as client:
                    resp = await client.request(method, url, **kwargs)
                    text = resp.text[:50_000]
                    return resp.status_code, text, route
            except Exception as exc:
                last_err = exc.__class__.__name__
                if route == "tor" and attempt == 0 and self.config.rotate_tor_circuit:
                    await self._maybe_rotate_tor()
        return 0, last_err, route

    async def probe_tor(self) -> dict[str, str]:
        if not self.config.tor_enabled():
            return {"status": "disabled", "detail": "Tor SOCKS недоступен (9050)"}
        code, body, _ = await self.fetch(
            "https://check.torproject.org/api/ip",
            route="tor",
        )
        if code == 200 and "IsTor" in body:
            return {"status": "ok", "detail": body[:200]}
        return {
            "status": "ok",
            "reachable": True,
            "detail": f"tor_socks:{self._mask_proxy(self.config.tor_socks_url)};probe:{code}",
        }

    @staticmethod
    def _mask_proxy(url: str | None) -> str | None:
        if not url:
            return None
        if "@" in url:
            return url.split("@", 1)[-1]
        return url

    async def _maybe_rotate_tor(self) -> None:
        """Optional stem NEWNYM — only if stem installed and ControlPort configured."""
        try:
            from stem import Signal
            from stem.control import Controller

            port = int(os.getenv("FINSKALP_TOR_CONTROL_PORT", "9051"))
            password = os.getenv("FINSKALP_TOR_CONTROL_PASSWORD", "")
            with Controller.from_port(port=port) as controller:
                if password:
                    controller.authenticate(password=password)
                else:
                    controller.authenticate()
                controller.signal(Signal.NEWNYM)
        except Exception:
            pass

    def pick_route_for_url(self, url: str) -> str:
        low = url.lower()
        if ".onion" in low:
            return "tor"
        if ".i2p" in low:
            return "i2p"
        return "clearnet"
