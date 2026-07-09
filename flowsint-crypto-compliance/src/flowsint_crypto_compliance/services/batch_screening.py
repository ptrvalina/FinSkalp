"""Batch wallet screening — CSV/JSONL onboarding at scale."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from flowsint_crypto_compliance.services.batch_parser import parse_address_rows
from flowsint_crypto_compliance.services.wallet_screening import (
    WalletScreeningRequest,
    WalletScreeningService,
)
from flowsint_crypto_compliance.storage.db_models import ComplianceBatchScreenJob
from flowsint_types.fiat_crypto import Chain

__all__ = ["BatchScreeningService", "parse_address_rows"]


class BatchScreeningService:
    def __init__(self, db: Session, screening: WalletScreeningService | None = None):
        self._db = db
        self._screening = screening or WalletScreeningService()

    def create_job(self, owner_id: uuid.UUID, rows: list[dict[str, str]]) -> ComplianceBatchScreenJob:
        job = ComplianceBatchScreenJob(
            owner_id=owner_id,
            status="pending",
            total=len(rows),
            processed=0,
            summary={"queued": len(rows)},
        )
        self._db.add(job)
        self._db.commit()
        self._db.refresh(job)
        return job

    async def run_job_sync(self, job_id: uuid.UUID, rows: list[dict[str, str]]) -> dict[str, Any]:
        job = self._db.get(ComplianceBatchScreenJob, job_id)
        if not job:
            raise ValueError("Job not found")
        job.status = "running"
        self._db.commit()

        results: list[dict[str, Any]] = []
        critical = high = medium = low = 0
        for i, row in enumerate(rows):
            try:
                chain = Chain(row["chain"].lower())
            except ValueError:
                chain = None
            try:
                out = await self._screening.screen(
                    WalletScreeningRequest(address=row["address"], chain=chain, depth=1, limit=25)
                )
                item = out.model_dump(mode="json")
            except Exception as exc:
                item = {"address": row["address"], "chain": row.get("chain"), "error": str(exc)[:200]}
            results.append(item)
            rl = (item.get("risk_level") or "low").lower()
            if rl in ("severe", "critical"):
                critical += 1
            elif rl == "high":
                high += 1
            elif rl == "medium":
                medium += 1
            else:
                low += 1
            job.processed = i + 1
            if (i + 1) % 50 == 0:
                self._db.commit()

        job.results = results
        job.summary = {
            "total": len(rows),
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
            "errors": sum(1 for r in results if r.get("error")),
        }
        job.status = "completed"
        job.finished_at = datetime.now(timezone.utc)
        self._db.commit()
        return job.summary or {}
