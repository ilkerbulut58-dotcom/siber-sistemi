"""Customer-visible validation layer tests."""

from __future__ import annotations

from app.benchmark.customer_validation import (
    CustomerVisibility,
    build_customer_validation_artifact,
    compute_customer_visible_metrics,
)
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


def test_passive_http_header_finding_confirmed_without_persisted_evidence():
    raw = RawFinding(
        source_tool="passive_http",
        source_rule_id="missing-header-strict-transport-security",
        title="Missing HSTS",
        description="missing",
        severity="medium",
        affected_url="https://benchmark-juice-proxy/",
        confidence="high",
    )
    artifact = build_customer_validation_artifact([raw])
    assert artifact.customer_visible_count == 1
    assert artifact.findings[0].visibility == CustomerVisibility.CONFIRMED


def test_customer_visible_metrics_excludes_needs_review_from_fp():
    confirmed = RawFinding(
        source_tool="passive_http",
        source_rule_id="missing-header-content-security-policy",
        title="Missing CSP",
        description="missing",
        severity="medium",
        affected_url="https://benchmark-crapi-proxy/",
        evidence={"missing_header": "content-security-policy"},
        confidence="high",
    )
    noise = RawFinding(
        source_tool="zap",
        source_rule_id="zap-40012",
        title="Cross Site Scripting",
        description="xss",
        severity="high",
        affected_url="https://benchmark-juice-proxy/",
        confidence="medium",
    )
    metrics = compute_customer_visible_metrics(
        true_positive_count=1,
        false_negative_count=0,
        raw_findings=[confirmed, noise],
    )
    assert metrics["customer_confirmed_false_positive_count"] == 0
    assert metrics["precision"] == 1.0
    assert metrics["customer_needs_review_count"] == 1


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
