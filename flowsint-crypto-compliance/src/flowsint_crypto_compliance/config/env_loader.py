"""Load repo .env without logging secrets."""

from __future__ import annotations

import os
from pathlib import Path


def _candidate_env_files() -> list[Path]:
    here = Path(__file__).resolve()
    roots = [
        Path.cwd(),
        here.parents[3],  # flowsint-crypto-compliance
        here.parents[4],  # monorepo root (flowsint)
    ]
    seen: set[Path] = set()
    files: list[Path] = []
    for root in roots:
        p = (root / ".env").resolve()
        if p in seen:
            continue
        seen.add(p)
        files.append(p)
    return files


def load_project_env(*, override: bool = False) -> bool:
    """Load first existing .env from cwd or package parents. Returns True if loaded."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        loaded = False
    else:
        loaded = False
        for env_file in _candidate_env_files():
            if env_file.is_file():
                load_dotenv(env_file, override=override)
                loaded = True
                break
    from flowsint_crypto_compliance.demo.combat_mode import apply_combat_env_defaults

    apply_combat_env_defaults()
    return loaded


def trongrid_key_configured() -> bool:
    return bool(os.getenv("TRONGRID_API_KEY", "").strip())
