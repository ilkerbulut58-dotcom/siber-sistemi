"""Analysis engine tests."""

import pytest

from app.analysis.correlation_engine import correlate_findings
from app.analysis.risk_engine import calculate_risk_score
from app.analysis.types import AnalyzedFinding
from app.scanners.base import RawFinding


def test_correlation_merges_same_header_from_multiple_tools() -> None:
    raw = [
        RawFinding(
            source_tool="passive_http",
            source_rule_id="missing-header-x-frame-options",
            title="Missing X-Frame-Options header",
            description="passive",
            severity="medium",
            affected_url="https://example.com/",
        ),
        RawFinding(
            source_tool="zap",
            source_rule_id="zap-10020",
            title="X-Frame-Options Header Not Set",
            description="zap",
            severity="medium",
            affected_url="https://example.com/",
        ),
    ]
    correlated = correlate_findings(raw)
    assert len(correlated) == 1
    assert correlated[0].correlation_key == "missing-header-x-frame-options"
    assert set(correlated[0].source_tools) == {"passive_http", "zap"}


def test_risk_score_increases_with_confidence_and_tools() -> None:
    low = AnalyzedFinding(
        correlation_key="missing-header-x-frame-options",
        title="test",
        description="test",
        severity="medium",
        affected_url="https://example.com/",
        verified_confidence="low",
        source_tools=["nuclei"],
        verification_status="unverified",
        exposure_score=1.0,
    )
    high = AnalyzedFinding(
        correlation_key="missing-header-x-frame-options",
        title="test",
        description="test",
        severity="medium",
        affected_url="https://example.com/",
        verified_confidence="high",
        source_tools=["passive_http", "zap"],
        verification_status="verified",
        exposure_score=1.0,
    )
    assert calculate_risk_score(high) > calculate_risk_score(low)


@pytest.mark.asyncio
async def test_verification_marks_missing_header_verified() -> None:
    from unittest.mock import patch

    from app.analysis.types import CorrelatedFinding
    from app.analysis.verification_engine import verify_findings

    correlated = [
        CorrelatedFinding(
            correlation_key="missing-header-x-frame-options",
            title="Missing X-Frame-Options",
            description="desc",
            severity="medium",
            affected_url="https://example.com/",
            source_tools=["passive_http"],
            source_rule_ids=["missing-header-x-frame-options"],
        )
    ]

    class Resp:
        headers = {"content-type": "text/html"}

    async def fake_get(url, cached):
        cached["response"] = Resp()
        return cached["response"]

    with patch("app.analysis.verification_engine._get_response", side_effect=fake_get):
        analyzed = await verify_findings("https://example.com/", correlated)

    assert analyzed[0].verification_status == "verified"
    assert analyzed[0].verified_confidence in ("medium", "high")
