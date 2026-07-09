"""Redis distributed lock for critical graph / label write sections."""

from __future__ import annotations

import os
import threading
import time
import uuid
from contextlib import contextmanager
from typing import Iterator


class DistributedLock:
    """Redis SET NX lock with in-process fallback for offline demo."""

    def __init__(self, ttl_sec: int = 120) -> None:
        self.ttl_sec = ttl_sec
        self._redis = None
        self._local: dict[str, tuple[str, float]] = {}
        self._local_lock = threading.Lock()
        url = os.getenv("REDIS_URL")
        if url:
            try:
                import redis

                self._redis = redis.from_url(url, decode_responses=True)
                self._redis.ping()
            except Exception:
                self._redis = None

    @contextmanager
    def acquire(self, resource: str, *, wait_sec: float = 30.0, poll_ms: float = 100.0) -> Iterator[bool]:
        token = uuid.uuid4().hex
        deadline = time.time() + wait_sec
        acquired = False
        try:
            while time.time() < deadline:
                if self._try_acquire(resource, token):
                    acquired = True
                    yield True
                    return
                time.sleep(poll_ms / 1000.0)
            yield False
        finally:
            if acquired:
                self._release(resource, token)

    def _try_acquire(self, resource: str, token: str) -> bool:
        key = f"lock:{resource}"
        if self._redis:
            try:
                return bool(self._redis.set(key, token, nx=True, ex=self.ttl_sec))
            except Exception:
                pass
        with self._local_lock:
            row = self._local.get(key)
            if row and row[1] > time.time():
                return False
            self._local[key] = (token, time.time() + self.ttl_sec)
            return True

    def _release(self, resource: str, token: str) -> None:
        key = f"lock:{resource}"
        if self._redis:
            try:
                script = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("del", KEYS[1])
                else
                    return 0
                end
                """
                self._redis.eval(script, 1, key, token)
                return
            except Exception:
                pass
        with self._local_lock:
            row = self._local.get(key)
            if row and row[0] == token:
                self._local.pop(key, None)


def lock_key(*parts: str) -> str:
    return ":".join(str(p) for p in parts if p)
