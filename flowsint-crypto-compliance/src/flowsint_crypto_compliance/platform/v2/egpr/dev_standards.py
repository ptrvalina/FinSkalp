"""RFC-0022 Ch.7 — development standards."""

from __future__ import annotations

from typing import Any


def dev_standards_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0022",
        "chapter": 7,
        "code_style": {
            "python": "ruff + black (line-length 100)",
            "typescript": "eslint + prettier",
            "naming": "snake_case (py), camelCase (ts), PascalCase (components)",
            "imports": "absolute within package, no circular deps",
        },
        "review_checklist": [
            {"id": "REV-01", "item": "Tests pass locally and in CI", "required": True},
            {"id": "REV-02", "item": "No secrets in diff", "required": True},
            {"id": "REV-03", "item": "RBAC on new mutate endpoints", "required": True},
            {"id": "REV-04", "item": "Pydantic models for request/response", "required": True},
            {"id": "REV-05", "item": "RFC reference in module docstring", "required": True},
            {"id": "REV-06", "item": "Completion doc updated if RFC scope", "required": True},
        ],
        "testing_standards": {
            "framework": "pytest",
            "min_tests_per_rfc": 8,
            "coverage_target": "stub — measure per module",
            "integration": "FastAPI TestClient for API routes",
            "env": "FINSKALP_ENTITY_STORE=memory for unit tests",
        },
        "security_review_checklist": [
            {"id": "SEC-01", "item": "Input validation (Pydantic bounds)", "required": True},
            {"id": "SEC-02", "item": "Authentication on protected routes", "required": True},
            {"id": "SEC-03", "item": "No SQL injection (ORM only)", "required": True},
            {"id": "SEC-04", "item": "Audit log for sensitive mutations", "required": True},
            {"id": "SEC-05", "item": "Dependency vulnerability scan", "required": True},
        ],
        "principle_ru": "Стандарты разработки — код, ревью, тесты и security checklist",
    }
