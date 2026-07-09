"""
Отсев мусора OSINT: репутация источника, дубликаты, низкая корреляция, спам-паттерны.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any

from flowsint_crypto_compliance.osint_core.open_source_collector import OpenMentionHit
from flowsint_crypto_compliance.osint_core.scalpel.legal_policy import (
    filter_legal_hits,
    is_blocked_source_type,
)

_SOURCE_REPUTATION: dict[str, float] = {
    "explorer_tag": 0.92,
    "otc_board": 0.88,
    "telegram": 0.72,
    "web": 0.70,
    "forum": 0.55,
    "paste": 0.35,
    "leak": 0.0,
    "darknet_index": 0.52,
    "username": 0.65,
    "correlation": 0.75,
    "clearnet_dork": 0.68,
}

_SPAM_PATTERNS = re.compile(
    r"(?i)(casino|bonus|airdrop\s*free|click\s*here|xxx|viagra|100%\s*profit)",
)

_JUNK_TITLE = re.compile(r"(?i)^(test|lorem|asdf|null|undefined|n/a)$")


@dataclass
class NoiseFilterResult:
    kept: list[OpenMentionHit] = field(default_factory=list)
    rejected: list[dict[str, Any]] = field(default_factory=list)
    junk_ratio: float = 0.0
    quality_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "kept_count": len(self.kept),
            "rejected_count": len(self.rejected),
            "junk_ratio": round(self.junk_ratio, 3),
            "quality_score": round(self.quality_score, 3),
            "rejected_sample": self.rejected[:10],
        }


def _embedding_junk_similarity(text: str, *, threshold: float = 0.92) -> bool:
    """Optional sentence-embedding filter (self-hosted sentence-transformers)."""
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]
        import numpy as np

        model_name = os.getenv("FINSKALP_JUNK_EMBED_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
        if not hasattr(_embedding_junk_similarity, "_model"):
            _embedding_junk_similarity._model = SentenceTransformer(model_name)  # type: ignore[attr-defined]
        model = _embedding_junk_similarity._model  # type: ignore[attr-defined]
        junk_refs = [
            "casino bonus click here free airdrop",
            "viagra 100% profit guaranteed",
            "lorem ipsum test placeholder",
        ]
        if not hasattr(_embedding_junk_similarity, "_junk_emb"):
            _embedding_junk_similarity._junk_emb = model.encode(junk_refs)  # type: ignore[attr-defined]
        junk_emb = _embedding_junk_similarity._junk_emb  # type: ignore[attr-defined]
        vec = model.encode([text[:500]])
        sims = np.dot(junk_emb, vec.T).flatten() / (
            np.linalg.norm(junk_emb, axis=1) * np.linalg.norm(vec) + 1e-9
        )
        return float(np.max(sims)) >= threshold
    except ImportError:
        return False
    except Exception:
        return False


def filter_osint_noise(
    hits: list[OpenMentionHit],
    *,
    min_confidence: float = 0.42,
    min_reputation: float = 0.45,
    target_address: str = "",
) -> NoiseFilterResult:
    kept: list[OpenMentionHit] = []
    rejected: list[dict[str, Any]] = []
    norm_target = target_address.casefold()

    legal_kept, legal_rejected = filter_legal_hits(hits)
    for rej in legal_rejected:
        rejected.append(rej)

    for h in legal_kept:
        if is_blocked_source_type(h.source_type):
            rejected.append({"hit": h.to_dict(), "reason": "blocked_source_type"})
            continue
        reason = _reject_reason(h, min_confidence=min_confidence, min_reputation=min_reputation)
        if reason:
            rejected.append({"hit": h.to_dict(), "reason": reason})
            continue
        blob = f"{h.title_ru} {h.excerpt_ru}"
        if os.getenv("FINSKALP_OSINT_EMBED_JUNK", "").lower() in ("1", "true", "yes"):
            if _embedding_junk_similarity(blob):
                rejected.append({"hit": h.to_dict(), "reason": "embedding_junk_similarity"})
                continue
        if norm_target and h.address:
            if h.address.casefold() != norm_target and h.source_type not in (
                "correlation",
                "username",
            ):
                rejected.append({"hit": h.to_dict(), "reason": "address_mismatch"})
                continue
        kept.append(h)

    kept = _dedupe_semantic(kept)
    total = len(kept) + len(rejected)
    junk_ratio = len(rejected) / total if total else 0.0
    quality = _quality_score(kept)

    return NoiseFilterResult(
        kept=kept,
        rejected=rejected,
        junk_ratio=junk_ratio,
        quality_score=quality,
    )


def _reject_reason(
    h: OpenMentionHit,
    *,
    min_confidence: float,
    min_reputation: float,
) -> str | None:
    if h.source_type in ("paste", "leak"):
        return f"illegal_source_category:{h.source_type}"
    rep = _SOURCE_REPUTATION.get(h.source_type, 0.55)
    if h.confidence < min_confidence:
        return f"low_confidence:{h.confidence:.2f}"
    if rep < min_reputation and h.confidence < 0.65:
        return f"low_reputation_source:{h.source_type}"
    blob = f"{h.title_ru} {h.excerpt_ru}"
    if _SPAM_PATTERNS.search(blob):
        return "spam_pattern"
    if _JUNK_TITLE.match(h.title_ru.strip()):
        return "junk_title"
    if len(h.excerpt_ru.strip()) < 8 and h.source_type not in ("explorer_tag",):
        return "empty_excerpt"
    return None


def _dedupe_semantic(hits: list[OpenMentionHit]) -> list[OpenMentionHit]:
    seen: set[str] = set()
    out: list[OpenMentionHit] = []
    for h in sorted(hits, key=lambda x: x.confidence, reverse=True):
        key = f"{h.source_type}:{h.risk_tag}:{h.excerpt_ru[:60].lower()}"
        if key in seen:
            continue
        seen.add(key)
        out.append(h)
    return out


def _quality_score(kept: list[OpenMentionHit]) -> float:
    if not kept:
        return 0.0
    reps = [_SOURCE_REPUTATION.get(h.source_type, 0.55) for h in kept]
    confs = [h.confidence for h in kept]
    indep = len({h.source_type for h in kept})
    return min(1.0, (sum(reps) / len(reps)) * 0.4 + (sum(confs) / len(confs)) * 0.4 + indep * 0.05)
