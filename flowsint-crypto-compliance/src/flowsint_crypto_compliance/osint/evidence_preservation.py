"""
Evidence preservation for URL OSINT findings — screenshot, HTML snapshot, Wayback check.

Self-hosted storage under FINSKALP_EVIDENCE_DIR; Playwright optional dependency.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

EVIDENCE_ROOT = Path(os.getenv("FINSKALP_EVIDENCE_DIR", "data/osint_evidence"))
WAYBACK_API = "https://archive.org/wayback/available"


@dataclass
class PreservedEvidence:
    url: str
    discovery_at: str
    screenshot_path: str | None = None
    screenshot_sha256: str | None = None
    html_path: str | None = None
    html_sha256: str | None = None
    wayback_url: str | None = None
    wayback_timestamp: str | None = None
    snapshot_api_url: str | None = None
    status: str = "pending"
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "discovery_at": self.discovery_at,
            "screenshot_path": self.screenshot_path,
            "screenshot_sha256": self.screenshot_sha256,
            "html_path": self.html_path,
            "html_sha256": self.html_sha256,
            "wayback_url": self.wayback_url,
            "wayback_timestamp": self.wayback_timestamp,
            "snapshot_api_url": self.snapshot_api_url,
            "report_link_ru": self.report_link_ru(),
            "status": self.status,
            "errors": self.errors,
        }

    def report_link_ru(self) -> str:
        parts = [f"Обнаружено: {self.discovery_at}"]
        if self.snapshot_api_url:
            parts.append(f"Снимок: {self.snapshot_api_url}")
        if self.screenshot_sha256:
            parts.append(f"SHA-256 PNG: {self.screenshot_sha256[:16]}…")
        if self.html_sha256:
            parts.append(f"SHA-256 HTML: {self.html_sha256[:16]}…")
        if self.wayback_url:
            parts.append(f"Wayback: {self.wayback_url}")
        return " · ".join(parts)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _evidence_dir(case_ref: str, url: str) -> Path:
    slug = hashlib.sha256(url.encode()).hexdigest()[:12]
    safe_case = "".join(c if c.isalnum() or c in "-_" else "_" for c in case_ref)[:48]
    d = EVIDENCE_ROOT / safe_case / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


async def check_wayback(url: str, *, timeout: float = 8.0) -> tuple[str | None, str | None]:
    """Query Internet Archive availability API (read-only, no API key)."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(WAYBACK_API, params={"url": url})
            if resp.status_code != 200:
                return None, None
            data = resp.json()
            snap = (data.get("archived_snapshots") or {}).get("closest") or {}
            if not snap.get("available"):
                return None, None
            return snap.get("url"), snap.get("timestamp")
    except Exception:
        return None, None


async def _fetch_html(url: str, *, timeout: float = 12.0) -> bytes | None:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "FinSkalp-OSINT/1.0 (evidence preservation)"})
            if resp.status_code >= 400:
                return None
            return resp.content
    except Exception:
        return None


async def _playwright_screenshot(url: str, dest: Path, *, timeout_ms: int = 15000) -> bool:
    try:
        from playwright.async_api import async_playwright  # type: ignore[import-untyped]
    except ImportError:
        return False
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            await page.screenshot(path=str(dest), full_page=True)
            await browser.close()
        return dest.is_file()
    except Exception:
        return False


async def preserve_url_evidence(
    url: str,
    *,
    case_ref: str,
    base_api_url: str = "",
) -> PreservedEvidence:
    """Capture HTML + optional screenshot; hash and store; check Wayback."""
    now = datetime.now(timezone.utc).isoformat()
    ev = PreservedEvidence(url=url, discovery_at=now)
    if not url or "://" not in url:
        ev.status = "skipped"
        ev.errors.append("invalid_url")
        return ev

    dest = _evidence_dir(case_ref, url)
    html_bytes = await _fetch_html(url)
    if html_bytes:
        html_path = dest / "page.html"
        html_path.write_bytes(html_bytes)
        ev.html_path = str(html_path)
        ev.html_sha256 = _sha256_bytes(html_bytes)

    png_path = dest / "screenshot.png"
    shot_ok = await _playwright_screenshot(url, png_path)
    if shot_ok:
        ev.screenshot_path = str(png_path)
        ev.screenshot_sha256 = _sha256_file(png_path)
    elif not html_bytes:
        ev.errors.append("playwright_unavailable_or_fetch_failed")

    wb_url, wb_ts = await check_wayback(url)
    ev.wayback_url = wb_url
    ev.wayback_timestamp = wb_ts

    meta_path = dest / "manifest.json"
    if base_api_url:
        ev.snapshot_api_url = (
            f"{base_api_url.rstrip('/')}/api/osint/evidence/"
            f"{quote(case_ref, safe='')}/{quote(ev.html_sha256 or ev.screenshot_sha256 or 'unknown', safe='')}"
        )
    meta_path.write_text(json.dumps(ev.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    ev.status = "ok" if (ev.html_sha256 or ev.screenshot_sha256) else "partial"
    return ev


async def preserve_mentions(
    mentions: list[dict[str, Any]],
    *,
    case_ref: str,
    base_api_url: str = "",
    max_urls: int = 5,
) -> list[dict[str, Any]]:
    """Preserve evidence for URL-bearing mentions (bounded concurrency)."""
    import asyncio

    urls: list[str] = []
    for m in mentions:
        u = (m.get("url") or "").strip()
        if u and u.startswith("http") and u not in urls:
            urls.append(u)
    urls = urls[:max_urls]

    async def _one(u: str) -> dict[str, Any]:
        ev = await preserve_url_evidence(u, case_ref=case_ref, base_api_url=base_api_url)
        return ev.to_dict()

    if not urls:
        return []
    return list(await asyncio.gather(*[_one(u) for u in urls]))


def load_evidence_manifest(case_ref: str, content_hash: str) -> dict[str, Any] | None:
    """Load preserved evidence by case + hash prefix."""
    safe_case = "".join(c if c.isalnum() or c in "-_" else "_" for c in case_ref)[:48]
    root = EVIDENCE_ROOT / safe_case
    if not root.is_dir():
        return None
    for sub in root.iterdir():
        manifest = sub / "manifest.json"
        if not manifest.is_file():
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            for key in ("html_sha256", "screenshot_sha256"):
                h = data.get(key) or ""
                if h.startswith(content_hash) or content_hash.startswith(h[:16]):
                    return data
        except Exception:
            continue
    return None
