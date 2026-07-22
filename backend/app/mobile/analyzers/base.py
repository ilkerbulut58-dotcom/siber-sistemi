"""Mobile analyzer interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MobileFinding:
    source_rule_id: str
    title: str
    description: str
    severity: str
    masvs_category: str | None = None
    affected_component: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    remediation: str | None = None
    confidence: str = "high"


@dataclass
class MobileAnalysisResult:
    application_name: str | None = None
    package_name: str | None = None
    version_name: str | None = None
    version_code: str | None = None
    findings: list[MobileFinding] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


class MobileAnalyzer(ABC):
    @abstractmethod
    def analyze(self, artifact_path: Path) -> MobileAnalysisResult:
        """Run static analysis on a mobile artifact."""
