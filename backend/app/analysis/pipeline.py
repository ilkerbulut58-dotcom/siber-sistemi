"""End-to-end finding analysis pipeline."""

from __future__ import annotations

from app.analysis.correlation_engine import correlate_findings
from app.analysis.risk_engine import score_findings
from app.analysis.types import AnalyzedFinding
from app.analysis.verification_engine import verify_findings
from app.scanners.base import RawFinding


async def analyze_scan_findings(
    target_url: str,
    raw_findings: list[RawFinding],
) -> list[AnalyzedFinding]:
    correlated = correlate_findings(raw_findings)
    verified = await verify_findings(target_url, correlated)
    return score_findings(verified)
