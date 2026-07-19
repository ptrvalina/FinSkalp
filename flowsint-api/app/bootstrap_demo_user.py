"""Idempotent demo operator seed for client previews and local demos."""

from __future__ import annotations

import os
import sys


def seed_demo_user() -> None:
    if os.getenv("SEED_DEMO_USER", "true").lower() in {"0", "false", "no"}:
        print("Skipping demo user seed (SEED_DEMO_USER=false)")
        return

    email = os.getenv("DEMO_USER_EMAIL", "analyst@example.com").strip().lower()
    password = os.getenv("DEMO_USER_PASSWORD", "FinSkalp2026!")
    if not email or not password:
        print("Skipping demo user seed (empty email/password)")
        return

    from flowsint_core.core.postgre_db import SessionLocal
    from flowsint_core.core.services.auth_service import create_auth_service
    from flowsint_core.core.services.exceptions import ConflictError

    db = SessionLocal()
    try:
        service = create_auth_service(db)
        try:
            service.register(email, password)
            print(f"Demo user seeded: {email}")
        except ConflictError:
            print(f"Demo user already present: {email}")
    except Exception as exc:  # noqa: BLE001 — startup must not abort API
        print(f"Demo user seed skipped due to error: {exc}", file=sys.stderr)
    finally:
        try:
            db.close()
        except Exception:  # noqa: BLE001
            pass


if __name__ == "__main__":
    seed_demo_user()
