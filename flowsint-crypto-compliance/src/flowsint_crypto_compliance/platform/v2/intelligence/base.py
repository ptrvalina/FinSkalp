"""Base intelligence engine — RFC-0004."""

from __future__ import annotations

from abc import ABC, abstractmethod

from flowsint_crypto_compliance.platform.v2.intelligence.types import (
    EngineAnalysisResult,
    EngineKind,
    IntelligenceContext,
)


class IntelligenceEngine(ABC):
    kind: EngineKind
    title_ru: str = ""
    maturity: str = "foundation"

    @abstractmethod
    def analyze(self, ctx: IntelligenceContext) -> EngineAnalysisResult:
        """Analyze using KG context only — no direct external API calls."""

    def manifest_entry(self) -> dict:
        return {
            "engine": self.kind.value,
            "title_ru": self.title_ru,
            "maturity": self.maturity,
        }
