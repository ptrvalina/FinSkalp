"""Display helpers for compliance case list / inbox rows."""

from __future__ import annotations

from typing import Any, Protocol


class _ProfileLike(Protocol):
    first_name: str | None
    last_name: str | None
    email: str


def profile_display_name(profile: _ProfileLike | None) -> str | None:
    if not profile:
        return None
    parts = [p.strip() for p in (profile.first_name, profile.last_name) if p and str(p).strip()]
    if parts:
        return " ".join(parts)
    email = (profile.email or "").strip()
    return email.split("@")[0] if email else None


def profile_name_ru(profile: _ProfileLike | None) -> str | None:
    """Russian-style analyst label: «Фамилия И.» or email local-part."""
    if not profile:
        return None
    last = (profile.last_name or "").strip()
    first = (profile.first_name or "").strip()
    if last and first:
        return f"{last} {first[0]}."
    if last:
        return last
    if first:
        return first
    return profile_display_name(profile)


def resolve_assignee_fields(
    assignee_id: Any,
    profiles: dict[Any, _ProfileLike],
) -> dict[str, str | None]:
    profile = profiles.get(assignee_id) if assignee_id else None
    return {
        "assignee_name": profile_display_name(profile),
        "analyst_name_ru": profile_name_ru(profile),
    }
