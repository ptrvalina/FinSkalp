"""RFC-0021 Ch.14 — operational backup runner (Wave 4, behind feature flag).

Creates a local backup bundle: manifest JSON, optional Postgres row-count
snapshot, and evidence directory inventory. Does not replace S3/pg_dump targets
in :func:`backup_manifest`; it records what was captured on this host.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_LAST_RUN: dict[str, Any] | None = None


def _backup_root() -> Path:
    raw = os.getenv("FINSKALP_BACKUP_DIR", "data/backups").strip() or "data/backups"
    return Path(raw)


def _last_run_path() -> Path:
    return _backup_root() / ".last_run.json"


def get_last_backup_status() -> dict[str, Any] | None:
    """Return in-memory last run, or hydrate from disk."""
    global _LAST_RUN
    if _LAST_RUN is not None:
        return dict(_LAST_RUN)
    path = _last_run_path()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        _LAST_RUN = data
        return dict(data)
    except Exception as exc:
        logger.warning("backup_runner: could not read %s: %s", path, exc)
        return None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _postgres_table_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    try:
        from sqlalchemy import text

        from flowsint_core.core.postgre_db import SessionLocal

        tables = (
            "eccf_evidence_records",
            "eccf_audit_log",
            "compliance_cases",
            "finskalp_evidence",
        )
        session = SessionLocal()
        try:
            for table in tables:
                try:
                    row = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    counts[table] = int(row or 0)
                except Exception:
                    counts[table] = -1
        finally:
            session.close()
    except Exception as exc:
        logger.warning("backup_runner: postgres counts skipped: %s", exc)
        counts["_error"] = str(exc)[:200]  # type: ignore[assignment]
    return counts


def _evidence_inventory() -> list[dict[str, Any]]:
    roots = [
        Path("data/osint_evidence"),
        Path("flowsint-crypto-compliance/data/osint_evidence"),
    ]
    items: list[dict[str, Any]] = []
    for root in roots:
        if not root.is_dir():
            continue
        for manifest in root.rglob("manifest.json"):
            try:
                rel = manifest.relative_to(root)
                items.append(
                    {
                        "path": str(manifest),
                        "sha256": _sha256_file(manifest),
                        "relative": str(rel),
                    }
                )
            except Exception as exc:
                items.append({"path": str(manifest), "error": str(exc)[:120]})
        break
    return items


def _maybe_pg_dump(dest: Path) -> dict[str, Any] | None:
    if os.getenv("FINSKALP_BACKUP_PG_DUMP", "").strip().lower() not in ("1", "true", "yes", "on"):
        return None
    db_url = os.getenv("DATABASE_URL", "").strip()
    if not db_url or not shutil.which("pg_dump"):
        return {"ok": False, "reason": "DATABASE_URL or pg_dump unavailable"}
    out = dest / "postgres.sql"
    try:
        subprocess.run(
            ["pg_dump", db_url, "-f", str(out)],
            check=True,
            capture_output=True,
            timeout=int(os.getenv("FINSKALP_BACKUP_PG_DUMP_TIMEOUT_SEC", "300")),
        )
        return {"ok": True, "path": str(out), "sha256": _sha256_file(out), "bytes": out.stat().st_size}
    except Exception as exc:
        logger.warning("backup_runner: pg_dump failed: %s", exc)
        return {"ok": False, "error": str(exc)[:200]}


def run_backup(*, dry_run: bool = False) -> dict[str, Any]:
    """Execute a backup cycle. When ``dry_run`` is True, only plan the bundle."""
    global _LAST_RUN
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    root = _backup_root()
    dest = root / stamp

    plan: dict[str, Any] = {
        "ok": True,
        "dry_run": dry_run,
        "started_at": started,
        "destination": str(dest),
        "targets": ["manifest", "postgres_counts", "evidence_inventory"],
    }

    if dry_run:
        plan["postgres_counts_preview"] = _postgres_table_counts()
        plan["evidence_file_count"] = len(_evidence_inventory())
        _LAST_RUN = plan
        return plan

    dest.mkdir(parents=True, exist_ok=True)
    manifest_body: dict[str, Any] = {
        "rfc": "RFC-0021",
        "chapter": 14,
        "backup_at": started,
        "postgres_counts": _postgres_table_counts(),
        "evidence_inventory": _evidence_inventory(),
    }
    pg_dump_result = _maybe_pg_dump(dest)
    if pg_dump_result is not None:
        manifest_body["pg_dump"] = pg_dump_result
        plan["targets"].append("pg_dump")

    manifest_path = dest / "backup_manifest.json"
    manifest_path.write_text(json.dumps(manifest_body, ensure_ascii=False, indent=2), encoding="utf-8")
    checksum = _sha256_file(manifest_path)

    result: dict[str, Any] = {
        **plan,
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "manifest_path": str(manifest_path),
        "manifest_sha256": checksum,
        "evidence_file_count": len(manifest_body["evidence_inventory"]),
    }
    _last_run_path().parent.mkdir(parents=True, exist_ok=True)
    _last_run_path().write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    _LAST_RUN = result
    logger.info(
        "backup_runner: completed bundle at %s sha256=%s evidence_files=%s",
        dest,
        checksum[:16],
        result["evidence_file_count"],
    )
    return result


def backup_runtime_status() -> dict[str, Any]:
    """Additive runtime block for ``GET /idoo/backup``."""
    last = get_last_backup_status()
    root = _backup_root()
    return {
        "runner_enabled": True,
        "backup_dir": str(root),
        "backup_dir_exists": root.is_dir(),
        "last_run": last,
        "pg_dump_enabled": os.getenv("FINSKALP_BACKUP_PG_DUMP", "").strip().lower()
        in ("1", "true", "yes", "on"),
    }
