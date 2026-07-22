"""Abstract AI provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.schemas import AIAnalysisResult, FindingAnalysisPayload


class AIProvider(ABC):
    @abstractmethod
    async def analyze_finding(self, payload: FindingAnalysisPayload) -> AIAnalysisResult:
        """Analyze a masked finding and return structured AI output."""

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Return True when the provider has credentials and is ready."""
