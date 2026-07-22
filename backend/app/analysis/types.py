"""Shared analysis types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.scanners.base import RawFinding


@dataclass
class CorrelatedFinding:
    correlation_key: str
    title: str
    description: str
    severity: str
    affected_url: str
    remediation: str | None = None
    confidence: str = "medium"
    evidence: dict[str, Any] = field(default_factory=dict)
    source_tools: list[str] = field(default_factory=list)
    source_rule_ids: list[str] = field(default_factory=list)
    raw_sources: list[RawFinding] = field(default_factory=list)
    risk_explanation: str | None = None
    remediation_steps: list[str] | None = None
    config_file_paths: list[str] | None = None
    config_snippet: str | None = None
    cvss_score: float | None = None


@dataclass
class AnalyzedFinding(CorrelatedFinding):
    verified_confidence: str = "medium"
    verification_status: str = "unverified"
    verification_notes: str | None = None
    risk_score: float = 0.0
    exposure_score: float = 1.0
    risk_breakdown: dict[str, Any] | None = None
    risk_model_version: str | None = None
    asset_type: str = "web"
    platform: str | None = None
    masvs_category: str | None = None
    affected_component: str | None = None
