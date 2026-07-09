"""RFC-0014 Ch.4 — collection scheduler."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


@dataclass
class ScheduledJob:
    job_id: str
    connector_id: str
    query: dict[str, Any] = field(default_factory=dict)
    case_ref: str | None = None
    tenant_id: str | None = None
    interval_seconds: int = 300
    max_retries: int = 3
    rate_limit_per_minute: int = 60
    quota_per_day: int = 10_000
    status: JobStatus = JobStatus.PENDING
    retries: int = 0
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    last_error: str | None = None
    runs_today: int = 0
    requests_this_minute: int = 0
    minute_window_start: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "connector_id": self.connector_id,
            "query": self.query,
            "case_ref": self.case_ref,
            "tenant_id": self.tenant_id,
            "interval_seconds": self.interval_seconds,
            "max_retries": self.max_retries,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "quota_per_day": self.quota_per_day,
            "status": self.status.value,
            "retries": self.retries,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "last_error": self.last_error,
            "runs_today": self.runs_today,
        }


class CollectionScheduler:
    """In-memory scheduler — automatic runs, retry, rate limit, quota."""

    def __init__(self) -> None:
        self._jobs: dict[str, ScheduledJob] = {}

    def schedule(
        self,
        *,
        connector_id: str,
        query: dict[str, Any] | None = None,
        case_ref: str | None = None,
        tenant_id: str | None = None,
        interval_seconds: int = 300,
        max_retries: int = 3,
        rate_limit_per_minute: int = 60,
        quota_per_day: int = 10_000,
    ) -> ScheduledJob:
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        job = ScheduledJob(
            job_id=job_id,
            connector_id=connector_id,
            query=dict(query or {}),
            case_ref=case_ref,
            tenant_id=tenant_id,
            interval_seconds=interval_seconds,
            max_retries=max_retries,
            rate_limit_per_minute=rate_limit_per_minute,
            quota_per_day=quota_per_day,
            next_run_at=now,
        )
        self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> ScheduledJob | None:
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[ScheduledJob]:
        return list(self._jobs.values())

    def _check_rate_limit(self, job: ScheduledJob) -> bool:
        now = time.time()
        if now - job.minute_window_start >= 60:
            job.minute_window_start = now
            job.requests_this_minute = 0
        if job.requests_this_minute >= job.rate_limit_per_minute:
            return False
        job.requests_this_minute += 1
        return True

    def _check_quota(self, job: ScheduledJob) -> bool:
        return job.runs_today < job.quota_per_day

    def due_jobs(self) -> list[ScheduledJob]:
        now = datetime.now(timezone.utc)
        due: list[ScheduledJob] = []
        for job in self._jobs.values():
            if job.status in (JobStatus.RUNNING,):
                continue
            if job.next_run_at and job.next_run_at <= now:
                if self._check_rate_limit(job) and self._check_quota(job):
                    due.append(job)
        return due

    def mark_running(self, job_id: str) -> None:
        job = self._jobs[job_id]
        job.status = JobStatus.RUNNING
        job.last_run_at = datetime.now(timezone.utc)

    def mark_completed(self, job_id: str) -> None:
        job = self._jobs[job_id]
        job.status = JobStatus.COMPLETED
        job.retries = 0
        job.runs_today += 1
        job.last_error = None
        from datetime import timedelta

        job.next_run_at = datetime.now(timezone.utc) + timedelta(seconds=job.interval_seconds)

    def mark_failed(self, job_id: str, error: str) -> None:
        job = self._jobs[job_id]
        job.last_error = error
        job.retries += 1
        if job.retries < job.max_retries:
            job.status = JobStatus.RETRY
            from datetime import timedelta

            job.next_run_at = datetime.now(timezone.utc) + timedelta(seconds=min(60 * job.retries, 300))
        else:
            job.status = JobStatus.FAILED

    def status(self) -> dict[str, Any]:
        jobs = self.list_jobs()
        return {
            "total_jobs": len(jobs),
            "pending": sum(1 for j in jobs if j.status == JobStatus.PENDING),
            "running": sum(1 for j in jobs if j.status == JobStatus.RUNNING),
            "completed": sum(1 for j in jobs if j.status == JobStatus.COMPLETED),
            "failed": sum(1 for j in jobs if j.status == JobStatus.FAILED),
            "retry": sum(1 for j in jobs if j.status == JobStatus.RETRY),
            "jobs": [j.to_dict() for j in jobs],
        }


_scheduler: CollectionScheduler | None = None


def get_collection_scheduler() -> CollectionScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = CollectionScheduler()
    return _scheduler
