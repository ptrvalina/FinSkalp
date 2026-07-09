"""RFC-0018 Ch.13 — centralized prompt rendering with version/history."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.eia.prompt_registry import get_prompt_template, list_prompt_versions
from flowsint_crypto_compliance.platform.v2.eia.security import redact_pii


def render_prompt(
    task_type: str,
    context: dict[str, Any],
    *,
    version: str | None = None,
) -> dict[str, Any]:
    """Render prompt from versioned template + investigation context."""
    template = get_prompt_template(task_type, version=version)
    if template is None:
        return {
            "ok": False,
            "error": f"no_template_for_{task_type}",
            "task_type": task_type,
        }

    safe_context = {k: redact_pii(str(v)) if isinstance(v, str) else v for k, v in context.items()}
    try:
        rendered = template.template.format(**safe_context)
    except KeyError as exc:
        return {
            "ok": False,
            "error": f"missing_template_key: {exc}",
            "task_type": task_type,
            "version": template.version,
        }

    return {
        "ok": True,
        "task_type": task_type,
        "version": template.version,
        "prompt": rendered,
        "template_author": template.author,
        "changelog": template.changelog,
        "available_versions": [v["version"] for v in list_prompt_versions(task_type)],
    }
