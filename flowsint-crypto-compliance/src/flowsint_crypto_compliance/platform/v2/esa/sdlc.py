"""RFC-0020 Ch.16 — secure SDLC checklist manifest."""

from __future__ import annotations

from typing import Any


def sdlc_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0020",
        "chapter": 16,
        "phases": {
            "design": [
                {"id": "SDL-01", "item": "Threat modeling (STRIDE)", "required": True, "status": "done"},
                {"id": "SDL-02", "item": "Data classification review", "required": True, "status": "done"},
                {"id": "SDL-03", "item": "RBAC matrix definition", "required": True, "status": "done"},
            ],
            "development": [
                {"id": "SDL-04", "item": "No secrets in code (vault only)", "required": True, "status": "done"},
                {"id": "SDL-05", "item": "Input validation (Pydantic)", "required": True, "status": "done"},
                {"id": "SDL-06", "item": "Dependency pinning (uv lock)", "required": True, "status": "done"},
                {"id": "SDL-07", "item": "SAST in CI pipeline", "required": True, "status": "partial"},
            ],
            "testing": [
                {"id": "SDL-08", "item": "Security unit tests per RFC", "required": True, "status": "done"},
                {"id": "SDL-09", "item": "RBAC/ABAC access tests", "required": True, "status": "done"},
                {"id": "SDL-10", "item": "Penetration test before prod", "required": True, "status": "open"},
            ],
            "deployment": [
                {"id": "SDL-11", "item": "TLS 1.2+ enforced", "required": True, "status": "done"},
                {"id": "SDL-12", "item": "Container image scanning", "required": True, "status": "partial"},
                {"id": "SDL-13", "item": "Secrets rotation on deploy", "required": True, "status": "partial"},
            ],
            "operations": [
                {"id": "SDL-14", "item": "Security monitoring alerts", "required": True, "status": "done"},
                {"id": "SDL-15", "item": "Incident response playbook", "required": True, "status": "partial"},
                {"id": "SDL-16", "item": "Quarterly access review", "required": True, "status": "open"},
            ],
        },
        "principle_ru": "Secure SDLC — безопасность на каждой фазе жизненного цикла",
    }
