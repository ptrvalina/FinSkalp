"""
Maigret CLI / library adapter для FinSkalp Scalpel Celery workers.

Установка: pip install maigret  OR  uv sync --extra maigret
Переменные: FINSKALP_MAIGRET_BIN, FINSKALP_MAIGRET_TOP_SITES, FINSKALP_MAIGRET_TIMEOUT
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from flowsint_crypto_compliance.osint_core.open_source_collector import OpenMentionHit


def maigret_available() -> bool:
    return bool(_resolve_maigret_bin())


def run_maigret(
    username: str,
    *,
    top_sites: int | None = None,
    use_tor: bool = False,
    timeout_sec: float | None = None,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.osint_core.scalpel.security import sanitize_username

    username = sanitize_username(username)

    top = top_sites or int(os.getenv("FINSKALP_MAIGRET_TOP_SITES", "120"))
    timeout = timeout_sec or float(os.getenv("FINSKALP_MAIGRET_TIMEOUT", "90"))
    bin_path = _resolve_maigret_bin()

    if bin_path:
        return _run_maigret_cli(
            bin_path, username, top_sites=top, use_tor=use_tor, timeout_sec=timeout
        )
    return _run_maigret_embedded(username)


def hits_from_maigret_result(result: dict[str, Any], *, address: str = "", chain: str = "") -> list[OpenMentionHit]:
    hits: list[OpenMentionHit] = []
    for row in result.get("hits") or []:
        if isinstance(row, OpenMentionHit):
            hits.append(row)
            continue
        hits.append(
            OpenMentionHit(
                source_type="username",
                source_name=row.get("site", "maigret"),
                title_ru=row.get("title_ru", f"Maigret · {row.get('site', '')}"),
                excerpt_ru=row.get("excerpt_ru", ""),
                url=row.get("url"),
                risk_tag=row.get("risk_tag", "social_profile"),
                confidence=float(row.get("confidence", 0.62)),
                address=address,
                chain=chain,
            )
        )
    return hits


def _resolve_maigret_bin() -> str | None:
    explicit = os.getenv("FINSKALP_MAIGRET_BIN")
    if explicit and Path(explicit).exists():
        return explicit
    found = shutil.which("maigret")
    return found


def _run_maigret_cli(
    bin_path: str,
    username: str,
    *,
    top_sites: int,
    use_tor: bool,
    timeout_sec: float,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="finskalp-maigret-") as tmp:
        report_path = Path(tmp) / f"{username}_report.json"
        cmd = [
            bin_path,
            username,
            "--json",
            "simple",
            "--folderoutput",
            tmp,
            "--top-sites",
            str(top_sites),
            "--timeout",
            str(int(min(30, timeout_sec / 3))),
        ]
        if use_tor or os.getenv("FINSKALP_TOR_SOCKS"):
            cmd.append("--tor")

        env = os.environ.copy()
        if os.getenv("FINSKALP_TOR_SOCKS"):
            env["ALL_PROXY"] = os.getenv("FINSKALP_TOR_SOCKS", "")

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                env=env,
                cwd=tmp,
            )
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "detail": f"maigret>{timeout_sec}s", "hits": []}
        except Exception as exc:
            return {"status": "error", "detail": str(exc)[:200], "hits": []}

        hits = _parse_maigret_output_dir(Path(tmp), username)
        if not hits and report_path.is_file():
            hits = _parse_maigret_json(report_path.read_text(encoding="utf-8", errors="replace"))

        return {
            "status": "ok" if hits else ("error" if proc.returncode != 0 else "miss"),
            "detail": (proc.stderr or proc.stdout or "")[:300],
            "hits": hits,
            "engine": "maigret_cli",
            "sites_checked": top_sites,
            "return_code": proc.returncode,
        }


def _parse_maigret_output_dir(out_dir: Path, username: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for path in out_dir.glob("*.json"):
        if path.name.startswith("."):
            continue
        hits.extend(_parse_maigret_json(path.read_text(encoding="utf-8", errors="replace")))
    for path in out_dir.glob("report_*.json"):
        hits.extend(_parse_maigret_json(path.read_text(encoding="utf-8", errors="replace")))
    if not hits:
        txt = out_dir / f"{username}.txt"
        if txt.is_file():
            hits.append(
                {
                    "site": "maigret_report",
                    "title_ru": f"Maigret отчёт · @{username}",
                    "excerpt_ru": txt.read_text(encoding="utf-8", errors="replace")[:500],
                    "url": None,
                    "confidence": 0.65,
                    "risk_tag": "username_dossier",
                }
            )
    return hits


def _parse_maigret_json(raw: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return hits

    if isinstance(data, dict):
        for site, info in data.items():
            if not isinstance(info, dict):
                continue
            if info.get("status") not in ("Claimed", "found", "OK", None):
                if str(info.get("status", "")).lower() in ("not found", "missing", "fail"):
                    continue
            url = info.get("url_user") or info.get("url") or info.get("link")
            if not url and not info.get("ids"):
                continue
            hits.append(
                {
                    "site": site,
                    "title_ru": f"Maigret: профиль на {site}",
                    "excerpt_ru": _format_maigret_ids(info),
                    "url": url,
                    "confidence": 0.72 if url else 0.58,
                    "risk_tag": "maigret_profile",
                }
            )
    return hits


def _format_maigret_ids(info: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("fullname", "location", "bio", "ids", "image"):
        val = info.get(key)
        if val:
            parts.append(f"{key}: {val}")
    return "; ".join(parts)[:400] or "Maigret: аккаунт найден"


def _run_maigret_embedded(username: str) -> dict[str, Any]:
    """Fallback когда maigret CLI не установлен — встроенный username_probe."""
    return {
        "status": "embedded",
        "detail": "maigret_cli_not_installed — используйте pip install maigret",
        "hits": [],
        "engine": "embedded_fallback",
        "username": username,
    }
