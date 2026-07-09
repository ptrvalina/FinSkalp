"""RFC-0014 Ch.16 — collector lifecycle stages."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.icf.types import CollectorStage


_LIFECYCLE_FLOW: tuple[CollectorStage, ...] = (
    CollectorStage.DRAFT,
    CollectorStage.TESTING,
    CollectorStage.PRODUCTION,
    CollectorStage.DEPRECATED,
    CollectorStage.ARCHIVED,
)

_STAGE_META: dict[CollectorStage, dict[str, str]] = {
    CollectorStage.DRAFT: {"label_ru": "Черновик", "description_ru": "Разработка адаптера"},
    CollectorStage.TESTING: {"label_ru": "Тестирование", "description_ru": "Проверка на стенде"},
    CollectorStage.PRODUCTION: {"label_ru": "Продакшн", "description_ru": "Доступен для сбора"},
    CollectorStage.DEPRECATED: {"label_ru": "Устаревший", "description_ru": "Заменён новым модулем"},
    CollectorStage.ARCHIVED: {"label_ru": "Архив", "description_ru": "Отключён"},
}


def lifecycle_manifest() -> dict[str, Any]:
    stages = []
    for stage in _LIFECYCLE_FLOW:
        meta = _STAGE_META.get(stage, {})
        stages.append({"id": stage.value, **meta})
    return {
        "rfc": "RFC-0014",
        "chapter": 16,
        "stages": stages,
        "flow": [s.value for s in _LIFECYCLE_FLOW],
    }


def can_transition(current: CollectorStage, target: CollectorStage) -> bool:
    order = {s: i for i, s in enumerate(_LIFECYCLE_FLOW)}
    return order.get(target, -1) >= order.get(current, 0)
