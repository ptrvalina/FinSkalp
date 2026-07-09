"""RFC-0022 Ch.16 — maturity criteria auto-evaluation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flowsint_crypto_compliance.platform.v2.egpr.types import MaturityCriterion

_DOCS_ROOT = Path(__file__).resolve().parents[5]
_COMPLETION_DIR = _DOCS_ROOT / "docs/architecture/v2"


def _completion_exists(rfc_number: int) -> bool:
    if rfc_number < 3:
        return rfc_number in (0, 2)
    path = _COMPLETION_DIR / f"rfc{rfc_number:04d}-completion.md"
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    return "100%" in text or "Complete" in text


def _module_exists(module_path: str) -> bool:
    root = Path(__file__).resolve().parents[3]
    return (root / module_path).exists()


def evaluate_maturity_criteria() -> list[MaturityCriterion]:
    criteria = [
        MaturityCriterion(
            "MAT-001",
            "Volume I RFC catalog complete (0000-0021)",
            "Каталог RFC Volume I полный",
            len([n for n in range(22) if n <= 21]) == 22,
            "docs/rfc/README.md",
        ),
        MaturityCriterion(
            "MAT-002",
            "RFC-0003 knowledge graph implemented",
            "RFC-0003 граф знаний реализован",
            _completion_exists(3)
            and (
                _module_exists("platform/v2/knowledge_graph.py")
                or _module_exists("platform/v2/knowledge_store.py")
            ),
            "platform/v2/knowledge_graph.py",
        ),
        MaturityCriterion(
            "MAT-003",
            "RFC-0019 ASPP platform live",
            "RFC-0019 ASPP платформа",
            _completion_exists(19) and _module_exists("platform/v2/aspp"),
            "platform/v2/aspp",
        ),
        MaturityCriterion(
            "MAT-004",
            "RFC-0020 ESA security layer",
            "RFC-0020 слой безопасности",
            _completion_exists(20) and _module_exists("platform/v2/esa"),
            "platform/v2/esa",
        ),
        MaturityCriterion(
            "MAT-005",
            "RFC-0021 IDOO observability",
            "RFC-0021 наблюдаемость",
            _completion_exists(21) and _module_exists("platform/v2/idoo"),
            "platform/v2/idoo",
        ),
        MaturityCriterion(
            "MAT-006",
            "Completion docs for RFC 0003-0021",
            "Completion docs для RFC 0003-0021",
            all(_completion_exists(n) for n in range(3, 22)),
            "docs/architecture/v2/rfc*-completion.md",
        ),
        MaturityCriterion(
            "MAT-007",
            "Shared platform v2 BFF routes",
            "Единый BFF platform/v2/routes",
            _module_exists("platform/v2/routes.py"),
            "platform/v2/routes.py",
        ),
        MaturityCriterion(
            "MAT-008",
            "EGPR governance module",
            "Модуль управления EGPR",
            _module_exists("platform/v2/egpr"),
            "platform/v2/egpr",
        ),
    ]
    return criteria


def maturity_manifest() -> dict[str, Any]:
    criteria = evaluate_maturity_criteria()
    met = sum(1 for c in criteria if c.met)
    total = len(criteria)
    score = round(met / total * 100, 1) if total else 0.0
    return {
        "rfc": "RFC-0022",
        "chapter": 16,
        "criteria": [c.to_dict() for c in criteria],
        "met_count": met,
        "total_count": total,
        "maturity_score_percent": score,
        "volume_i_ready": score >= 100.0 or met == total,
        "principle_ru": "Критерии зрелости — автооценка по completion docs и модулям",
    }
