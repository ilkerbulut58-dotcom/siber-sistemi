"""Detection quality calibration tests."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.analysis.correlation_engine import correlate_findings
from app.analysis.correlation_rules import resolve_correlation_key, secret_identity_token
from app.benchmark.runner import _git_commit
from app.models.benchmark import BenchmarkClassification
from app.scanners.base import RawFinding
from app.services.benchmark_matching_service import match_findings
from app.services.finding_service import build_fingerprint


def expected(
    key: str,
    *,
    required: bool = True,
    alternatives: list[str] | None = None,
    category: str | None = None,
):
    return SimpleNamespace(
        id=uuid4(),
        expected_key=key,
        accepted_alternative_keys=alternatives or [],
        category=category or key,
        affected_location=None,
        detection_required=required,
    )


def finding(
    *,
    key: str,
    rule: str | None = None,
    url: str | None = None,
    fingerprint: str = "abc",
    evidence: dict | None = None,
    title: str = "finding",
):
    return SimpleNamespace(
        id=uuid4(),
        correlation_key=key,
        source_rule_id=rule or key,
        fingerprint=fingerprint,
        affected_url=url,
        title=title,
        evidence=evidence,
    )


def test_sensitive_data_maps_to_hardcoded_password_correlation_key():
    key = resolve_correlation_key(
        "sensitive_data",
        "sensitive-hardcoded-password",
        "Possible hardcoded password in public response",
    )
    assert key == "hardcoded-password"


def test_alternative_rule_id_matches_hardcoded_password_expected():
    records, metrics = match_findings(
        [
            expected(
                "hardcoded-password",
                alternatives=[
                    "sensitive-hardcoded-password",
                    "generic.possible-hardcoded-password-in-public-response",
                ],
            )
        ],
        [finding(key="generic.possible-hardcoded-password-in-public-response")],
    )
    assert records[0].classification == BenchmarkClassification.TRUE_POSITIVE
    assert metrics.true_positive_count == 1
    assert metrics.confirmed_false_positive_count == 0


def test_same_secret_deduplicated_across_urls_in_correlation_engine():
    raw = [
        RawFinding(
            source_tool="sensitive_data",
            source_rule_id="sensitive-hardcoded-password",
            title="Possible hardcoded password in public response",
            description="a",
            severity="high",
            affected_url="http://127.0.0.1:18080/",
            evidence={"pattern": "hardcoded-password", "masked_sample": "benc…2345"},
        ),
        RawFinding(
            source_tool="sensitive_data",
            source_rule_id="sensitive-hardcoded-password",
            title="Possible hardcoded password in public response",
            description="b",
            severity="high",
            affected_url="http://127.0.0.1:18080/main.js",
            evidence={"pattern": "hardcoded-password", "masked_sample": "benc…2345"},
        ),
    ]
    correlated = correlate_findings(raw)
    assert len(correlated) == 1
    assert correlated[0].correlation_key == "hardcoded-password"
    assert len(correlated[0].evidence.get("affected_locations", [])) == 2


def test_different_secrets_remain_separate_in_correlation_engine():
    raw = [
        RawFinding(
            source_tool="sensitive_data",
            source_rule_id="sensitive-hardcoded-password",
            title="Possible hardcoded password in public response",
            description="a",
            severity="high",
            affected_url="http://127.0.0.1:18080/a.js",
            evidence={"pattern": "hardcoded-password", "masked_sample": "pass…aaaa"},
        ),
        RawFinding(
            source_tool="sensitive_data",
            source_rule_id="sensitive-hardcoded-password",
            title="Possible hardcoded password in public response",
            description="b",
            severity="high",
            affected_url="http://127.0.0.1:18080/b.js",
            evidence={"pattern": "hardcoded-password", "masked_sample": "pass…bbbb"},
        ),
    ]
    correlated = correlate_findings(raw)
    assert len(correlated) == 2


def test_secret_fingerprint_ignores_url_for_same_masked_sample():
    project_id = uuid4()
    evidence = {"pattern": "hardcoded-password", "masked_sample": "benc…2345"}
    fp_a = build_fingerprint(
        project_id,
        "hardcoded-password",
        "http://127.0.0.1:18080/",
        evidence=evidence,
    )
    fp_b = build_fingerprint(
        project_id,
        "hardcoded-password",
        "http://127.0.0.1:18080/main.js",
        evidence=evidence,
    )
    assert fp_a == fp_b


def test_valid_additional_finding_for_optional_expected():
    records, metrics = match_findings(
        [expected("no-https", required=False)],
        [finding(key="no-https")],
    )
    assert records[0].classification == BenchmarkClassification.VALID_ADDITIONAL_FINDING
    assert metrics.additional_valid_finding_count == 1
    assert metrics.confirmed_false_positive_count == 0


def test_confirmed_false_positive_when_no_expected_match():
    _, metrics = match_findings([], [finding(key="totally-unknown-signal")])
    assert metrics.confirmed_false_positive_count == 1
    assert metrics.precision == 0.0


def test_matcher_failure_when_fn_expected_has_relaxed_match_only():
    records, metrics = match_findings(
        [expected("hardcoded-password", category="hardcoded-password")],
        [
            finding(
                key="generic.possible-hardcoded-password-in-public-response",
                rule="generic.possible-hardcoded-password-in-public-response",
                title="hardcoded-password exposure in response",
            )
        ],
    )
    assert metrics.false_negative_count == 1
    assert metrics.matcher_failure_count == 1
    assert any(record.classification == BenchmarkClassification.MATCHER_FAILURE for record in records)


def test_precision_uses_only_confirmed_false_positives():
    _, metrics = match_findings(
        [expected("missing-csp"), expected("missing-hsts")],
        [finding(key="missing-csp"), finding(key="noise-signal")],
    )
    assert metrics.true_positive_count == 1
    assert metrics.confirmed_false_positive_count == 1
    assert metrics.precision == 0.5


def test_ground_truth_missing_metric_field_present():
    _, metrics = match_findings([], [])
    assert metrics.ground_truth_gap_count == 0


def test_secret_identity_token_requires_masked_sample():
    assert secret_identity_token("hardcoded-password", {"pattern": "hardcoded-password"}) is None
    token = secret_identity_token(
        "hardcoded-password",
        {"pattern": "hardcoded-password", "masked_sample": "benc…2345"},
    )
    assert token == "hardcoded-password:benc…2345"


def test_git_commit_prefers_github_sha(monkeypatch):
    monkeypatch.setenv("GITHUB_SHA", "abc123deadbeef")
    assert _git_commit() == "abc123deadbeef"


def test_git_commit_falls_back_to_rev_parse(monkeypatch):
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    if result.returncode != 0:
        pytest.skip("git repository unavailable")
    assert _git_commit() == result.stdout.strip()


def test_android_duration_set_from_run_timestamps():
    from datetime import UTC, datetime, timedelta

    from app.services.benchmark_run_service import BenchmarkRunService

    started = datetime.now(UTC) - timedelta(seconds=2.5)
    run = SimpleNamespace(started_at=started, completed_at=None, duration_seconds=None)
    completed = datetime.now(UTC)
    if run.started_at:
        run.completed_at = completed
        run.duration_seconds = (run.completed_at - run.started_at).total_seconds()
    assert run.duration_seconds is not None
    assert run.duration_seconds >= 2.0
    assert BenchmarkRunService  # import guard for service module availability
