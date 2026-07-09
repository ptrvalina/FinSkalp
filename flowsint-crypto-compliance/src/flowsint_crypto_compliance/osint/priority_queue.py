"""Priority queue for rate-limited OSINT sources — ordered by case SLA urgency."""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

_SLA_PRIORITY = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "normal": 3,
    "low": 4,
}

_WORKFLOW_BOOST = {
    "triage": 0,
    "investigating": 0,
    "pending_filing": 1,
    "new": 2,
    "filed": 3,
    "archived": 4,
}


@dataclass(order=True)
class PrioritizedOsintJob:
    sort_key: tuple[int, float, str] = field(compare=True)
    case_ref: str = field(compare=False)
    address: str = field(compare=False)
    chain: str = field(compare=False)
    collector_id: str = field(compare=False)
    priority: str = field(compare=False, default="normal")
    workflow_status: str = field(compare=False, default="new")
    sla_breached: bool = field(compare=False, default=False)
    enqueued_at: str = field(compare=False, default="")


class OsintPriorityQueue:
    """Min-heap: lower sort_key = higher priority."""

    def __init__(self) -> None:
        self._heap: list[PrioritizedOsintJob] = []

    def enqueue(
        self,
        *,
        case_ref: str,
        address: str,
        chain: str,
        collector_id: str,
        priority: str = "normal",
        workflow_status: str = "new",
        sla_breached: bool = False,
        due_at: datetime | None = None,
    ) -> None:
        pr = _SLA_PRIORITY.get(priority, 3)
        wf = _WORKFLOW_BOOST.get(workflow_status, 2)
        sla_penalty = -2 if sla_breached else 0
        due_ts = due_at.timestamp() if due_at else float("inf")
        key = (pr + wf + sla_penalty, due_ts, case_ref)
        heapq.heappush(
            self._heap,
            PrioritizedOsintJob(
                sort_key=key,
                case_ref=case_ref,
                address=address,
                chain=chain,
                collector_id=collector_id,
                priority=priority,
                workflow_status=workflow_status,
                sla_breached=sla_breached,
                enqueued_at=datetime.utcnow().isoformat() + "Z",
            ),
        )

    def pop(self) -> PrioritizedOsintJob | None:
        if not self._heap:
            return None
        return heapq.heappop(self._heap)

    def peek(self) -> PrioritizedOsintJob | None:
        return self._heap[0] if self._heap else None

    def size(self) -> int:
        return len(self._heap)

    def to_list(self) -> list[dict[str, Any]]:
        return [
            {
                "case_ref": j.case_ref,
                "address": j.address,
                "chain": j.chain,
                "collector_id": j.collector_id,
                "priority": j.priority,
                "workflow_status": j.workflow_status,
                "sla_breached": j.sla_breached,
                "enqueued_at": j.enqueued_at,
            }
            for j in sorted(self._heap)
        ]


_global_queue = OsintPriorityQueue()


def get_osint_priority_queue() -> OsintPriorityQueue:
    return _global_queue
