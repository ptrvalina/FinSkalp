"""
Celery task idempotency — prevent duplicate cases/alerts on retry.

Uses Redis SET NX when available; in-process dict for demo/offline.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from typing import Any


class IdempotencyStore:
    TTL_SEC = int(os.getenv("FINSKALP_IDEMPOTENCY_TTL_SEC", "86400"))

    def __init__(self) -> None:
        self._local: dict[str, tuple[str, Any, float]] = {}
        self._lock = threading.Lock()
        self._redis = None
        url = os.getenv("REDIS_URL")
        if url:
            try:
                import redis

                self._redis = redis.from_url(url, decode_responses=True)
                self._redis.ping()
            except Exception:
                self._redis = None

    def _key(self, scope: str, idempotency_key: str) -> str:
        digest = hashlib.sha256(f"{scope}:{idempotency_key}".encode()).hexdigest()[:32]
        return f"idempotency:{scope}:{digest}"

    def acquire(self, scope: str, idempotency_key: str) -> str:
        """Return 'new', 'done', or 'in_progress'."""
        rk = self._key(scope, idempotency_key)
        if self._redis:
            try:
                if self._redis.get(rk + ":done"):
                    return "done"
                if not self._redis.set(rk + ":lock", "1", nx=True, ex=600):
                    return "in_progress"
                return "new"
            except Exception:
                pass
        with self._lock:
            row = self._local.get(rk)
            if row:
                status, _val, _exp = row
                return status
            self._local[rk] = ("in_progress", None, time.time() + self.TTL_SEC)
            return "new"

    def complete(self, scope: str, idempotency_key: str, result: Any) -> None:
        rk = self._key(scope, idempotency_key)
        payload = json.dumps(result, default=str)
        if self._redis:
            try:
                pipe = self._redis.pipeline()
                pipe.set(rk + ":done", payload, ex=self.TTL_SEC)
                pipe.delete(rk + ":lock")
                pipe.execute()
                return
            except Exception:
                pass
        with self._lock:
            self._local[rk] = ("done", result, time.time() + self.TTL_SEC)

    def get_result(self, scope: str, idempotency_key: str) -> Any:
        rk = self._key(scope, idempotency_key)
        if self._redis:
            try:
                raw = self._redis.get(rk + ":done")
                if raw:
                    return json.loads(raw)
            except Exception:
                pass
        with self._lock:
            row = self._local.get(rk)
            if row and row[0] == "done":
                return row[1]
        return None

    def release(self, scope: str, idempotency_key: str) -> None:
        rk = self._key(scope, idempotency_key)
        if self._redis:
            try:
                self._redis.delete(rk + ":lock")
            except Exception:
                pass
        with self._lock:
            self._local.pop(rk, None)


def make_idempotency_key(*parts: str) -> str:
    return ":".join(str(p) for p in parts if p)


def run_idempotent(scope: str, idempotency_key: str, fn):
    store = IdempotencyStore()
    state = store.acquire(scope, idempotency_key)
    if state == "done":
        cached = store.get_result(scope, idempotency_key)
        if cached is not None:
            return cached
    if state == "in_progress":
        cached = store.get_result(scope, idempotency_key)
        if cached is not None:
            return cached
        raise RuntimeError(f"Task already in progress: {idempotency_key}")
    try:
        result = fn()
        store.complete(scope, idempotency_key, result)
        return result
    except Exception:
        store.release(scope, idempotency_key)
        raise
