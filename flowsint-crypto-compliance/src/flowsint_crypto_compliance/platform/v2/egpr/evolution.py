"""RFC-0022 Ch.18 — evolution rules (RFC→ADR→Review→Test→Board)."""

from __future__ import annotations

from typing import Any


def evolution_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0022",
        "chapter": 18,
        "workflow": {
            "name": "RFC→ADR→Review→Test→Board",
            "steps": [
                {
                    "step": 1,
                    "phase": "rfc_draft",
                    "actor": "author",
                    "artifact": "docs/rfc/RFC-NNNN-*.md",
                    "gate": "template compliance",
                },
                {
                    "step": 2,
                    "phase": "adr_decision",
                    "actor": "architect",
                    "artifact": "ADR record in adr_registry",
                    "gate": "options analysis documented",
                },
                {
                    "step": 3,
                    "phase": "technical_review",
                    "actor": "domain_lead",
                    "artifact": "review comments",
                    "gate": "no blocking issues",
                },
                {
                    "step": 4,
                    "phase": "implementation",
                    "actor": "engineering",
                    "artifact": "platform/v2/{module}/",
                    "gate": "min 8 tests per RFC",
                },
                {
                    "step": 5,
                    "phase": "test_validation",
                    "actor": "qa",
                    "artifact": "tests/test_rfcNNNN_*.py",
                    "gate": "pytest pass",
                },
                {
                    "step": 6,
                    "phase": "board_approval",
                    "actor": "architecture_board",
                    "artifact": "completion doc 100%",
                    "gate": "quorum vote",
                },
            ],
        },
        "constraints": [
            "No architecture change without Architecture Board approval",
            "Every RFC must link to at least one strategic principle",
            "Completion doc required before COMPLETE stage",
            "Breaking API changes require semver major bump",
        ],
        "principle_ru": "Правила эволюции — RFC → ADR → Review → Test → Board",
    }
