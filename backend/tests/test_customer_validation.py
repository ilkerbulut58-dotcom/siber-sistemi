"""Customer-visible validation layer tests."""

from __future__ import annotations

from app.benchmark.customer_validation import CustomerVisibility, build_customer_validation_artifact
from app.scanners.base import RawFinding


def test_header_finding_is_confirmed():
    raw = RawFinding(
        source_tool="passive_http",
        source_rule_id="missing-header-content-security-policy",
        title="Missing CSP",
        description="missing",
        severity="medium",
        affected_url="https://benchmark-crapi-proxy/",
        evidence={"missing_header": "content-security-policy"},
        confidence="high",
    )
    artifact = build_customer_validation_artifact([raw])
    assert artifact.customer_visible_count == 1
    assert artifact.findings[0].visibility == CustomerVisibility.CONFIRMED


def test_low_evidence_finding_needs_review():
    raw = RawFinding(
        source_tool="zap",
        source_rule_id="zap-99999",
        title="Unknown",
        description="unknown",
        severity="medium",
        affected_url="https://benchmark-juice-proxy/",
        confidence="low",
    )
    artifact = build_customer_validation_artifact([raw])
    assert artifact.findings[0].visibility == CustomerVisibility.NEEDS_REVIEW
    assert artifact.suppressions
