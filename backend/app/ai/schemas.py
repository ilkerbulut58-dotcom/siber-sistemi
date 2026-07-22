"""Structured AI analysis response schema."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ConfidenceLabel = Literal["unverified", "verified", "likely_false_positive"]


class AIAnalysisResult(BaseModel):
    summary: str = Field(..., min_length=10, max_length=2000)
    remediation: str = Field(..., min_length=10, max_length=4000)
    confidence_label: ConfidenceLabel = "unverified"


class FindingAnalysisPayload(BaseModel):
    title: str
    severity: str
    affected_url: str | None = None
    correlation_key: str | None = None
    risk_score: float | None = None
    cvss_score: float | None = None
    confidence: str | None = None
    verification_status: str | None = None
    source_tools: list[str] = Field(default_factory=list)
    risk_explanation: str | None = None
    remediation: str | None = None
    remediation_steps: list[str] = Field(default_factory=list)
    config_snippet: str | None = None
    config_file_paths: list[str] = Field(default_factory=list)
    evidence_summary: str | None = None
