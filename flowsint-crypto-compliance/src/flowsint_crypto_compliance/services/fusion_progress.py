from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator, Callable, Awaitable

FUSION_STEPS: tuple[tuple[str, str], ...] = (
    ("ingest", "Приём и нормализация источников"),
    ("entity", "Резолвер сущностей"),
    ("merge", "Слияние: суверенные > банк > VASP > реестр"),
    ("graph", "Построение графа доказательств"),
    ("link", "Склейка фиат ↔ крипто"),
    ("attribute", "Суверенная атрибуция (РФ/СНГ)"),
    ("detect", "Детектор + XGBoost risk score"),
    ("report", "Материалы для 115-ФЗ"),
)


@dataclass(frozen=True)
class FusionProgressEvent:
    step: str
    label_ru: str
    status: str
    detail_ru: str = ""

    def to_sse(self) -> dict[str, str]:
        return {
            "step": self.step,
            "label_ru": self.label_ru,
            "status": self.status,
            "detail_ru": self.detail_ru,
        }


ProgressCallback = Callable[[FusionProgressEvent], Awaitable[None] | None]


async def stream_fusion_steps(
    runner: Callable[[ProgressCallback], Awaitable[dict]],
) -> AsyncIterator[dict[str, str]]:
    events: list[FusionProgressEvent] = []

    async def _emit(event: FusionProgressEvent) -> None:
        events.append(event)

    for step_id, label in FUSION_STEPS:
        yield FusionProgressEvent(step_id, label, "running").to_sse()

    result = await runner(_emit)

    for step_id, label in FUSION_STEPS:
        detail = next((e.detail_ru for e in events if e.step == step_id and e.detail_ru), "")
        yield FusionProgressEvent(step_id, label, "done", detail).to_sse()

    yield {
        "step": "complete",
        "label_ru": "Fusion завершён",
        "status": "done",
        "detail_ru": f"attributions={len(result.get('attributions', []))}",
        "result": "ready",
    }
