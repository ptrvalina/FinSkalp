"""Offline multilingual OSINT — language detection and optional Argos translation."""

from __future__ import annotations

import re
from typing import Any

# CIS jurisdiction phone / ID patterns beyond RU-only
_RE_KZ_PHONE = re.compile(r"\b\+7\s?7\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b")
_RE_UA_PHONE = re.compile(r"\b\+380[\s\-]?\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b")
_RE_BY_PHONE = re.compile(r"\b\+375[\s\-]?\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b")
_RE_UZ_PHONE = re.compile(r"\b\+998[\s\-]?\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b")
_RE_KG_INN = re.compile(r"\b(?:ИНН[:\s]*)?(\d{14})\b", re.I)
_RE_AM_TIN = re.compile(r"\b(?:ՀՎՀՀ|TIN)[:\s]*(\d{8})\b", re.I)

_CYRILLIC = re.compile(r"[\u0400-\u04FF]")
_LATIN = re.compile(r"[A-Za-z]")


def detect_language(text: str) -> str:
    """Lightweight offline language guess (ru / en / mixed / other)."""
    if not text or len(text.strip()) < 4:
        return "unknown"
    cyr = len(_CYRILLIC.findall(text))
    lat = len(_LATIN.findall(text))
    if cyr > lat * 1.5:
        return "ru"
    if lat > cyr * 1.5:
        return "en"
    if cyr and lat:
        return "mixed"
    return "other"


def translate_to_russian(text: str, *, source_lang: str | None = None) -> dict[str, Any]:
    """
    Translate text to Russian via argos-translate if installed; else return original.
    """
    src = source_lang or detect_language(text)
    if src in ("ru", "unknown") or not text.strip():
        return {
            "original": text,
            "translated_ru": text,
            "source_lang": src,
            "translation_available": False,
        }
    try:
        import argostranslate.package  # type: ignore[import-untyped]
        import argostranslate.translate  # type: ignore[import-untyped]

        lang_map = {"en": "en", "mixed": "en", "other": "en"}
        from_code = lang_map.get(src, "en")
        translated = argostranslate.translate.translate(text, from_code, "ru")
        return {
            "original": text,
            "translated_ru": translated,
            "source_lang": src,
            "translation_available": True,
            "engine": "argos-translate",
        }
    except ImportError:
        return {
            "original": text,
            "translated_ru": text,
            "source_lang": src,
            "translation_available": False,
            "fallback_ru": "Перевод недоступен (установите optional-dep osint-quality)",
        }
    except Exception as exc:
        return {
            "original": text,
            "translated_ru": text,
            "source_lang": src,
            "translation_available": False,
            "error": exc.__class__.__name__,
        }


def enrich_mention_text(mention: dict[str, Any]) -> dict[str, Any]:
    """Add language + Russian translation fields to a mention dict."""
    blob = f"{mention.get('title_ru', '')} {mention.get('excerpt_ru', '')}".strip()
    lang = detect_language(blob)
    tr = translate_to_russian(blob, source_lang=lang)
    out = dict(mention)
    out["detected_lang"] = lang
    out["text_ru"] = tr.get("translated_ru") or blob
    out["translation"] = tr
    return out


def extract_cis_entities(text: str) -> dict[str, list[str]]:
    """Supplement entity_extractor with CIS jurisdiction patterns."""
    return {
        "phones_kz": _RE_KZ_PHONE.findall(text),
        "phones_ua": _RE_UA_PHONE.findall(text),
        "phones_by": _RE_BY_PHONE.findall(text),
        "phones_uz": _RE_UZ_PHONE.findall(text),
        "inn_kg": _RE_KG_INN.findall(text),
        "tin_am": _RE_AM_TIN.findall(text),
    }
