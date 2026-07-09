#!/usr/bin/env python3
"""Synthetic compliance volume for pgHero / load testing (entity_labels, audit_log, cases)."""

from __future__ import annotations

import argparse
import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed synthetic compliance rows for DB perf audit")
    parser.add_argument("--entity-labels", type=int, default=50_000)
    parser.add_argument("--cases", type=int, default=10_000)
    parser.add_argument("--audit-rows", type=int, default=100_000)
    args = parser.parse_args()

    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL required", file=sys.stderr)
        raise SystemExit(1)

    from sqlalchemy import create_engine, text

    engine = create_engine(url)
    now = datetime.now(timezone.utc)
    owner = uuid.uuid4()

    with engine.begin() as conn:
        print(f"Inserting {args.cases} cases…")
        case_ids = []
        for i in range(args.cases):
            cid = uuid.uuid4()
            case_ids.append(cid)
            conn.execute(
                text(
                    """
                    INSERT INTO compliance_cases (id, case_ref, owner_id, workflow_status, status, created_at, updated_at)
                    VALUES (:id, :ref, :owner, :ws, 'open', :ts, :ts)
                    ON CONFLICT (case_ref) DO NOTHING
                    """
                ),
                {
                    "id": cid,
                    "ref": f"FS-SYN-{i:08d}",
                    "owner": owner,
                    "ws": random.choice(["new", "triage", "investigating", "pending_filing", "filed"]),
                    "ts": now - timedelta(days=random.randint(0, 365)),
                },
            )

        print(f"Inserting {args.entity_labels} entity_labels…")
        for i in range(args.entity_labels):
            conn.execute(
                text(
                    """
                    INSERT INTO compliance_entity_labels
                    (id, chain, address, label, category, confidence, source, risk_score, status, added_at)
                    VALUES (:id, :chain, :addr, :label, 'unknown', 0.7, :src, :risk, 'active', :ts)
                    ON CONFLICT DO NOTHING
                    """
                ),
                {
                    "id": uuid.uuid4(),
                    "chain": random.choice(["tron", "eth", "btc"]),
                    "addr": f"T{'X' * 33}{i % 10}",
                    "label": f"synthetic_entity_{i}",
                    "src": random.choice(["graphsense", "ofac_sdn", "analyst_confirmed", "opensanctions"]),
                    "risk": round(random.uniform(10, 95), 1),
                    "ts": now - timedelta(days=random.randint(0, 180)),
                },
            )

        print(f"Inserting {args.audit_rows} audit_log rows…")
        for i in range(args.audit_rows):
            conn.execute(
                text(
                    """
                    INSERT INTO compliance_audit_log (id, case_id, action, payload, created_at)
                    VALUES (:id, :case_id, :action, '{}'::jsonb, :ts)
                    """
                ),
                {
                    "id": uuid.uuid4(),
                    "case_id": random.choice(case_ids) if case_ids else None,
                    "action": random.choice(["case_created", "workflow_transition", "report_export", "attribution_review"]),
                    "ts": now - timedelta(hours=random.randint(0, 8760)),
                },
            )

    print("Done. Open pgHero at http://localhost:8088 to review indexes and slow queries.")


if __name__ == "__main__":
    main()
