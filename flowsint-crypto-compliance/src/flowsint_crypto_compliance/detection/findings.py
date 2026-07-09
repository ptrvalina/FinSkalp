from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class IllegalFlowFinding:
    severity: str  # critical | high | medium | low
    code: str
    title_ru: str
    description_ru: str
    addresses: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0
