"""RFC-0022 — governance constraints."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.egpr.types import StrategicPrinciple

_FORBIDDEN_WITHOUT_BOARD = frozenset({
    "architecture_change",
    "new_core_layer",
    "breaking_api_change",
    "security_model_change",
    "data_model_breaking_change",
    "bypass_rfc_process",
    "skip_adr_for_major_decision",
    "deploy_without_board_approval",
})


def constraints_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0022",
        "chapter": 20,
        "rule": "no_architecture_change_without_board",
        "rule_ru": "Никаких архитектурных изменений без решения Архитектурного совета",
        "principles": [p.value for p in StrategicPrinciple],
        "forbidden_without_board": sorted(_FORBIDDEN_WITHOUT_BOARD),
        "forbidden_ru": {
            "architecture_change": "Архитектурное изменение без совета",
            "new_core_layer": "Новый core-слой без RFC",
            "breaking_api_change": "Breaking API change без major version",
            "security_model_change": "Изменение модели безопасности",
            "data_model_breaking_change": "Breaking change модели данных",
            "bypass_rfc_process": "Обход процесса RFC",
            "skip_adr_for_major_decision": "Пропуск ADR для крупного решения",
            "deploy_without_board_approval": "Развёртывание без одобрения совета",
        },
        "enforcement": {
            "ci_gate": "RFC reference in PR title for arch changes",
            "board_api": "/api/platform/v2/egpr/rfc/{rfc_id}/transition",
            "adr_required": True,
        },
        "principle_ru": "Ограничения — архитектурные изменения только через Architecture Board",
    }


def assert_governance_constraint(action: str) -> None:
    if action in _FORBIDDEN_WITHOUT_BOARD:
        raise ValueError(
            f"Forbidden without Architecture Board approval: {action}. "
            "Submit review via architecture_board.submit_board_review()."
        )
