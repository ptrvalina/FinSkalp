"""RFC-0022 Ch.3 — Architecture Board charter and review workflow."""

from __future__ import annotations

import uuid
from typing import Any

from flowsint_crypto_compliance.platform.v2.egpr.types import BoardReviewRequest

_BOARD_MEMBERS = [
    {"role": "chief_architect", "name": "Architecture Lead", "vote": True},
    {"role": "security_officer", "name": "CISO", "vote": True},
    {"role": "platform_lead", "name": "Platform Engineering", "vote": True},
    {"role": "compliance_lead", "name": "Compliance Domain", "vote": True},
    {"role": "product_owner", "name": "Product Owner", "vote": True},
]

_pending_reviews: list[BoardReviewRequest] = []


def board_charter() -> dict[str, Any]:
    return {
        "rfc": "RFC-0022",
        "chapter": 3,
        "name": "FinSkalp Architecture Board",
        "name_ru": "Архитектурный совет FinSkalp",
        "mandate": (
            "Govern enterprise architecture decisions, RFC acceptance, "
            "ADR ratification, and cross-cutting technical standards."
        ),
        "mandate_ru": (
            "Управление архитектурными решениями, принятием RFC, "
            "ратификацией ADR и сквозными техническими стандартами."
        ),
        "members": _BOARD_MEMBERS,
        "quorum": 3,
        "meeting_cadence": "bi-weekly",
        "decision_types": [
            "rfc_acceptance",
            "adr_ratification",
            "architecture_exception",
            "release_approval",
            "tech_debt_prioritization",
        ],
        "principle_ru": "Архитектурный совет — единая точка принятия архитектурных решений",
    }


def submit_board_review(
    *,
    subject: str,
    requester: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stub workflow — submit item for Architecture Board review."""
    request = BoardReviewRequest(
        request_id=str(uuid.uuid4()),
        subject=subject,
        requester=requester,
        status="pending",
        details=details or {},
    )
    _pending_reviews.append(request)
    return {
        "ok": True,
        "review": request.to_dict(),
        "message": "Review submitted to Architecture Board (not configured)",
    }


def list_pending_reviews() -> dict[str, Any]:
    return {
        "ok": True,
        "count": len(_pending_reviews),
        "reviews": [r.to_dict() for r in _pending_reviews],
    }


def board_workflow_manifest() -> dict[str, Any]:
    return {
        **board_charter(),
        "workflow": {
            "steps": [
                {"step": 1, "action": "submit_rfc_or_adr", "actor": "author"},
                {"step": 2, "action": "technical_review", "actor": "domain_lead"},
                {"step": 3, "action": "board_review", "actor": "architecture_board"},
                {"step": 4, "action": "decision_recorded", "actor": "secretary"},
                {"step": 5, "action": "implementation_tracking", "actor": "platform_team"},
            ],
            "sla_days": 14,
            "escalation": "chief_architect",
        },
        "pending_count": len(_pending_reviews),
    }
