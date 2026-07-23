"""Blind holdout matching tests."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.benchmark.blind_matching import match_blind_holdout_findings
from app.models.benchmark import AutomationSupport


def _expected(key: str):
    return SimpleNamespace(
        id=uuid4(),
        expected_key=key,
        accepted_alternative_keys=[],
        category=key,
        affected_location="/",
        detection_required=True,
        automation_support=AutomationSupport.SUPPORTED,
    )


def _finding(key: str, *, severity: str = "medium"):
    return SimpleNamespace(
        id=uuid4(),
        correlation_key=key,
        source_rule_id=key,
        fingerprint=f"{key}:url",
        affected_url="http://127.0.0.1:18080/",
        title=key,
        source_tool="passive_http",
        severity=severity,
        source_tools=["passive_http"],
    )


def test_blind_reclassifies_valid_out_of_holdout_as_additional():
    expected = [_expected("missing-header-x-frame-options")]
    actual = [
        _finding("missing-header-x-frame-options"),
        _finding("missing-header-content-security-policy"),
        _finding("missing-header-strict-transport-security"),
    ]
    _, metrics, analysis = match_blind_holdout_findings(expected, actual)
    assert metrics.true_positive_count == 1
    assert metrics.false_negative_count == 0
    assert metrics.confirmed_false_positive_count == 0
    assert metrics.additional_valid_finding_count == 2
    assert metrics.precision == 1.0
    assert len(analysis) == 2


def test_blind_informational_zap_noise_not_counted_as_fp():
    expected = [_expected("missing-header-x-frame-options")]
    actual = [
        _finding("missing-header-x-frame-options"),
        _finding("generic.cross-domain-javascript-source-file-inclusion", severity="info"),
    ]
    _, metrics, _ = match_blind_holdout_findings(expected, actual)
    assert metrics.confirmed_false_positive_count == 0
    assert metrics.informational_count >= 1
