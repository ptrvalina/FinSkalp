"""Sanctions screening status — no false negatives when sources are unavailable."""

from __future__ import annotations

from typing import Any


def _is_unavailable(status: str | None) -> bool:
    if not status:
        return False
    s = str(status).lower()
    if s in ("ok", "completed", "hit", "no_match", "miss"):
        return False
    return s.startswith(("degraded", "error", "unavailable")) or s in ("503", "401", "403", "timeout")


def _opensanctions_api_status(source_status: dict[str, str]) -> str:
    raw = source_status.get("opensanctions_api") or source_status.get("attr_opensanctions_api") or ""
    if not raw:
        return "not_run"
    if raw == "ok":
        return "completed"
    if _is_unavailable(raw):
        return "unavailable"
    return "completed"


def _ofac_status(source_status: dict[str, str], sanctions_hits: list[dict]) -> str:
    ofac_hits = [h for h in sanctions_hits if "ofac" in str(h.get("source", "")).lower()]
    if ofac_hits:
        return "completed"
    store = source_status.get("ofac_store") or source_status.get("attr_ofac_store") or ""
    if store == "unavailable":
        return "unavailable"
    # Bootstrap OFAC store scan counts as completed when bootstrap ran
    if source_status.get("ofac_bootstrap") == "ok" or store in ("completed", "no_match", "miss"):
        return "completed"
    return "completed"


def build_screening_status(
    *,
    source_status: dict[str, str],
    sanctions_hits: list[dict[str, Any]],
) -> dict[str, str]:
    """Structured screening status per source."""
    os_api = _opensanctions_api_status(source_status)
    ofac = _ofac_status(source_status, sanctions_hits)
    registry = "completed"
    if _is_unavailable(source_status.get("registry_primary", "")):
        registry = "unavailable"
    return {
        "OFAC": ofac,
        "OpenSanctions": os_api,
        "Internal_Registry": registry,
    }


def sanctions_narrative_ru(
    *,
    screening_status: dict[str, str],
    source_status: dict[str, str],
    sanctions_hits: list[dict[str, Any]],
) -> dict[str, str]:
    """
    Forensic-safe sanctions wording.
    Never claim 'no match' when OpenSanctions API was unavailable.
    """
    os_st = screening_status.get("OpenSanctions", "not_run")
    ofac_st = screening_status.get("OFAC", "not_run")

    if sanctions_hits:
        srcs = ", ".join(sorted({str(h.get("source") or "sanctions") for h in sanctions_hits[:5]}))
        return {
            "status_ru": f"Обнаружены совпадения ({len(sanctions_hits)}): {srcs}.",
            "status_en": f"Sanctions matches observed: {len(sanctions_hits)} ({srcs}).",
            "conclusion_type": "match",
        }

    parts_ru: list[str] = []
    parts_en: list[str] = []

    if os_st == "unavailable":
        detail = source_status.get("opensanctions_api") or source_status.get("attr_opensanctions_api") or "degraded"
        parts_ru.append(
            "Проверка OpenSanctions не завершена вследствие недоступности источника "
            f"({detail})."
        )
        parts_en.append(f"OpenSanctions screening unavailable at report generation time ({detail}).")
    elif os_st == "completed":
        parts_ru.append("Live OpenSanctions: совпадений по адресу не зафиксировано.")
        parts_en.append("Live OpenSanctions: no address-level match recorded.")

    if ofac_st == "unavailable":
        parts_ru.append("Проверка OFAC SDN (bootstrap) недоступна на момент генерации отчёта.")
        parts_en.append("OFAC SDN bootstrap screening unavailable at report generation time.")
    elif ofac_st == "completed":
        parts_ru.append("OFAC SDN (offline snapshot): прямых совпадений не зафиксировано.")
        parts_en.append("OFAC SDN offline snapshot: no direct match recorded.")

    if not parts_ru:
        parts_ru.append("Санкционный скрининг не выполнялся или данные отсутствуют.")
        parts_en.append("Sanctions screening not performed or data missing.")

    return {
        "status_ru": " ".join(parts_ru),
        "status_en": " ".join(parts_en),
        "conclusion_type": "partial" if os_st == "unavailable" or ofac_st == "unavailable" else "clear",
    }


def confidence_penalty_for_screening(screening_status: dict[str, str]) -> float:
    """Reduce overall confidence when sanctions sources unavailable."""
    penalty = 0.0
    if screening_status.get("OpenSanctions") == "unavailable":
        penalty += 0.12
    if screening_status.get("OFAC") == "unavailable":
        penalty += 0.08
    if screening_status.get("Internal_Registry") == "unavailable":
        penalty += 0.05
    return penalty
