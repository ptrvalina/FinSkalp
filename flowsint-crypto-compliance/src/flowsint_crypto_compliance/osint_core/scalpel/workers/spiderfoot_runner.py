"""
SpiderFoot adapter — автоматизация модулей OSINT (200+ источников).

Установка: клон SpiderFoot + FINSKALP_SPIDERFOOT_SF=path/to/sf.py
Или: pip install spiderfoot (если доступен в окружении).
"""

from __future__ import annotations

import csv
import io
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from flowsint_crypto_compliance.osint_core.open_source_collector import OpenMentionHit

_DEFAULT_MODULES = (
    "sfp_dnsresolve",
    "sfp_whois",
    "sfp_pageinfo",
    "sfp_spider",
    "sfp_hashes",
    "sfp_email",
)


def spiderfoot_available() -> bool:
    return bool(_resolve_sf_script())


def run_spiderfoot(
    target: str,
    *,
    modules: list[str] | None = None,
    timeout_sec: float | None = None,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.osint_core.scalpel.security import sanitize_spiderfoot_target

    target = sanitize_spiderfoot_target(target)

    sf = _resolve_sf_script()
    timeout = timeout_sec or float(os.getenv("FINSKALP_SPIDERFOOT_TIMEOUT", "120"))
    mod_list = modules or _modules_from_env()

    if not sf:
        return _run_spiderfoot_compat(target, mod_list)

    out_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", prefix="sf-")
    out_path = out_file.name
    out_file.close()

    cmd = [
        "python",
        sf,
        "-s",
        target,
        "-o",
        "tab",
        "-q",
        "-f",
        out_path,
    ]
    for m in mod_list:
        cmd.extend(["-m", m])

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(Path(sf).parent),
        )
        raw = Path(out_path).read_text(encoding="utf-8", errors="replace")
        hits = _parse_spiderfoot_tsv(raw, target)
        return {
            "status": "ok" if hits else "miss",
            "detail": (proc.stderr or "")[:300],
            "hits": hits,
            "engine": "spiderfoot_cli",
            "modules": mod_list,
            "return_code": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "detail": f"spiderfoot>{timeout}s", "hits": []}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)[:200], "hits": []}
    finally:
        try:
            Path(out_path).unlink(missing_ok=True)
        except OSError:
            pass


def hits_from_spiderfoot_result(
    result: dict[str, Any], *, address: str = "", chain: str = ""
) -> list[OpenMentionHit]:
    hits: list[OpenMentionHit] = []
    for row in result.get("hits") or []:
        hits.append(
            OpenMentionHit(
                source_type="web",
                source_name=f"SpiderFoot:{row.get('module', 'sf')}",
                title_ru=row.get("title_ru", "SpiderFoot finding"),
                excerpt_ru=row.get("excerpt_ru", ""),
                url=row.get("url"),
                risk_tag=row.get("risk_tag", "spiderfoot_intel"),
                confidence=float(row.get("confidence", 0.6)),
                address=address or row.get("target", ""),
                chain=chain,
            )
        )
    return hits


def _resolve_sf_script() -> str | None:
    explicit = os.getenv("FINSKALP_SPIDERFOOT_SF")
    if explicit and Path(explicit).is_file():
        return explicit
    for candidate in ("sf.py", "spiderfoot/sf.py"):
        found = shutil.which(candidate)
        if found:
            return found
    return None


def _modules_from_env() -> list[str]:
    raw = os.getenv("FINSKALP_SPIDERFOOT_MODULES", "")
    if raw.strip():
        return [m.strip() for m in raw.split(",") if m.strip()]
    return list(_DEFAULT_MODULES)


def _parse_spiderfoot_tsv(raw: str, target: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    if not raw.strip():
        return hits
    reader = csv.reader(io.StringIO(raw), delimiter="\t")
    for row in reader:
        if len(row) < 4:
            continue
        source, data, module, conf = row[0], row[1], row[2], row[3] if len(row) > 3 else "60"
        if not data or data == target:
            continue
        try:
            confidence = min(0.9, float(conf) / 100.0)
        except ValueError:
            confidence = 0.55
        hits.append(
            {
                "module": module,
                "title_ru": f"SpiderFoot · {module}",
                "excerpt_ru": f"{source}: {data}",
                "url": data if data.startswith("http") else None,
                "confidence": confidence,
                "risk_tag": "spiderfoot_intel",
                "target": target,
            }
        )
    return hits[:80]


def _run_spiderfoot_compat(target: str, modules: list[str]) -> dict[str, Any]:
    """
    Встроенный compat-слой когда sf.py не установлен —
    эмулирует ключевые модули через httpx (DNS/WHOIS/page meta).
    """
    import httpx

    hits: list[dict[str, Any]] = []
    status = "compat"
    detail = "spiderfoot_not_installed — compat layer"

    if target.startswith("http") or "." in target and not target.startswith("T"):
        try:
            with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                resp = client.get(
                    target if target.startswith("http") else f"https://{target}"
                )
                if resp.status_code == 200:
                    title = ""
                    if "<title>" in resp.text:
                        title = resp.text.split("<title>", 1)[1].split("</title>", 1)[0][:120]
                    hits.append(
                        {
                            "module": "sfp_pageinfo_compat",
                            "title_ru": f"Compat pageinfo · {target[:30]}",
                            "excerpt_ru": f"HTTP {resp.status_code}, title: {title}",
                            "url": str(resp.url),
                            "confidence": 0.58,
                            "risk_tag": "web_intel",
                            "target": target,
                        }
                    )
        except Exception as exc:
            detail = f"compat_error:{exc.__class__.__name__}"

    return {
        "status": status,
        "detail": detail,
        "hits": hits,
        "engine": "spiderfoot_compat",
        "modules": modules,
    }
