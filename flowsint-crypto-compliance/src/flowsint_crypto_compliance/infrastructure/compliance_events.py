"""
Event-driven compliance core — Redis Streams with in-memory fallback.

Every case hit, risk-score change, fusion completion publishes here.
UI subscribes via SSE/WebSocket relay endpoints.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from collections import deque
from typing import Any, AsyncIterator, Iterator

STREAM_KEY = "compliance:events"
MAX_MEMORY_EVENTS = 500


class ComplianceEventBus:
    def __init__(self) -> None:
        self._memory: deque[dict[str, Any]] = deque(maxlen=MAX_MEMORY_EVENTS)
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

    def publish(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
        *,
        severity: str = "info",
        correlation_id: str | None = None,
        text_ru: str | None = None,
    ) -> dict[str, Any]:
        event = {
            "id": str(uuid.uuid4()),
            "type": event_type,
            "schema_version": "1.0.0",
            "severity": severity,
            "payload": payload or {},
            "correlation_id": correlation_id,
            "text_ru": text_ru or _default_text_ru(event_type, payload or {}),
            "source": (payload or {}).get("source", "finskalp"),
            "ts": time.time(),
        }
        if payload and payload.get("operator_event_type"):
            event["operator_event_type"] = payload["operator_event_type"]
            event["operator_schema_version"] = payload.get("operator_schema_version", "1.0.0")
        if payload and payload.get("v2_event_type"):
            event["platform_event_type"] = payload["v2_event_type"]
            event["platform_schema_version"] = "2.0.0"
        with self._lock:
            self._memory.appendleft(event)
        if self._redis:
            try:
                self._redis.xadd(
                    STREAM_KEY,
                    {"json": json.dumps(event, ensure_ascii=False)},
                    maxlen=10_000,
                    approximate=True,
                )
                self._redis.publish("compliance:live", json.dumps(event, ensure_ascii=False))
            except Exception:
                pass
        return event

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._memory)[:limit]

    def stream_events(self, *, block_ms: int = 2000) -> Iterator[dict[str, Any]]:
        """Blocking iterator for SSE (Redis XREAD or memory poll)."""
        seen: set[str] = set()
        last_id = "0-0"
        if self._redis:
            try:
                tail = self._redis.xrevrange(STREAM_KEY, count=1)
                if tail:
                    last_id = tail[0][0]
            except Exception:
                pass
        while True:
            if self._redis:
                try:
                    rows = self._redis.xread({STREAM_KEY: last_id}, block=block_ms, count=5)
                    for _stream, messages in rows or []:
                        for msg_id, fields in messages:
                            last_id = msg_id
                            raw = fields.get("json") or fields.get("data")
                            if isinstance(raw, bytes):
                                raw = raw.decode()
                            ev = json.loads(raw)
                            if ev["id"] not in seen:
                                seen.add(ev["id"])
                                yield ev
                    continue
                except Exception:
                    pass
            with self._lock:
                for ev in self._memory:
                    if ev["id"] not in seen:
                        seen.add(ev["id"])
                        yield ev
                        break
            time.sleep(min(max(block_ms / 1000, 0.5), 2.5))

    async def async_stream_events(self) -> AsyncIterator[dict[str, Any]]:
        import asyncio

        for ev in self.stream_events():
            yield ev
            await asyncio.sleep(0)


def _default_text_ru(event_type: str, payload: dict[str, Any]) -> str:
    mapping = {
        "case_new": f"Новое дело · {payload.get('alert_code', payload.get('case_ref', '—'))}",
        "case_transition": f"Workflow · {payload.get('case_ref', '—')} → {payload.get('target', '—')}",
        "case_investigation_done": f"Расследование завершено · {payload.get('case_ref', '—')}",
        "investigation_completed": (
            f"ФинСкальп · {payload.get('case_ref', '—')} · "
            f"риск {payload.get('risk_score', '—')}/100"
        ),
        "fusion_completed": f"Fusion завершён · {payload.get('case_ref', '—')}",
        "fusion_failed": f"Fusion ошибка · {payload.get('error', '')[:80]}",
        "bank_feed_ingested": f"Банковский фид · {payload.get('count', 0)} записей",
        "wallet_screened": f"Скрининг · риск {payload.get('risk_score', '—')}/100",
        "alert_created": f"Алерт · {payload.get('alert_code', '—')}",
        "risk_score_changed": f"Risk score · {payload.get('address', '')[:12]}… → {payload.get('score', '—')}",
        "report_downloaded": f"Отчёт скачан · {payload.get('report_id', '—')}",
        "case_status_changed": f"Статус дела · {payload.get('status', '—')}",
    }
    return mapping.get(event_type, event_type)


_bus: ComplianceEventBus | None = None


def get_event_bus() -> ComplianceEventBus:
    global _bus
    if _bus is None:
        _bus = ComplianceEventBus()
    return _bus
