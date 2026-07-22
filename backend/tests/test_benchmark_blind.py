"""Phase 11.4 blind benchmark infrastructure tests."""

from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import uuid4

from app.benchmark.blind import (
    BLIND_SECRET_ENV,
    evaluate_blind_benchmark,
    load_public_metadata,
    public_metadata_dict,
    seal_ground_truth,
    try_load_blind_fixture,
    verify_artifact_hash,
)
from app.benchmark.manifests import repo_benchmarks_root

BLIND_YAML = """\
target: web-security-test-1-blind
target_type: web
target_reference: http://127.0.0.1:18080/
environment: benchmark-blind
expected_findings:
  - expected_key: blind-holdout-clickjacking-signal
    title: Clickjacking exposure holdout
    category: missing-header-x-frame-options
    severity: medium
    affected_location: /
    detection_required: true
    accepted_alternative_keys:
      - missing-x-frame-options
  - expected_key: blind-holdout-referrer-leak
    title: Referrer leakage holdout
    category: missing-header-referrer-policy
    severity: low
    affected_location: /
    detection_required: true
"""


def test_public_metadata_has_no_plaintext_ground_truth():
    metadata = load_public_metadata()
    payload = public_metadata_dict(metadata)
    assert "expected_findings" not in payload
    assert metadata.expected_finding_count == 3
    assert metadata.fixture_reference["suite"] == "web-smoke"
    assert metadata.artifact_file.endswith(".enc")


def test_committed_artifact_hash_matches_metadata():
    metadata = load_public_metadata()
    path = repo_benchmarks_root() / "blind" / metadata.artifact_file
    assert verify_artifact_hash(path, metadata.artifact_sha256)


def test_blind_benchmark_skips_without_secret(monkeypatch):
    monkeypatch.delenv(BLIND_SECRET_ENV, raising=False)
    result = evaluate_blind_benchmark([])
    assert result.status == "skipped"
    assert result.skip_reason == "secret_missing"
    assert result.metrics is None
    assert "without producing synthetic results" in (result.message or "")


def test_blind_roundtrip_with_test_secret(tmp_path, monkeypatch):
    secret = "unit-test-blind-secret"
    blob = seal_ground_truth(secret, BLIND_YAML)
    enc_path = tmp_path / "holdout.enc"
    enc_path.write_bytes(blob)

    metadata_path = tmp_path / "metadata.yaml"
    metadata_path.write_text(
        f"""\
version: "1.0.0"
name: test-blind
description: test
artifact_file: holdout.enc
artifact_sha256: {__import__("hashlib").sha256(blob).hexdigest()}
ground_truth_version: "1.0.0"
expected_finding_count: 2
fixture_reference:
  suite: web-smoke
""",
        encoding="utf-8",
    )

    monkeypatch.setenv(BLIND_SECRET_ENV, secret)
    monkeypatch.setattr("app.benchmark.blind.metadata_path", lambda: metadata_path)
    monkeypatch.setattr("app.benchmark.blind.blind_root", lambda: tmp_path)
    fixture, skip_reason = try_load_blind_fixture()
    assert skip_reason is None
    assert fixture is not None
    assert len(fixture.expected_findings) == 2


def test_blind_evaluation_counts_true_positives(monkeypatch):
    monkeypatch.setenv(BLIND_SECRET_ENV, "siber-blind-ground-truth-v1")
    findings = [
        SimpleNamespace(
            id=uuid4(),
            correlation_key="missing-header-x-frame-options",
            source_rule_id="10020",
            fingerprint="fp1",
            affected_url="http://127.0.0.1:18080/",
            title="XFO",
            source_tools=["zap"],
        )
    ]
    result = evaluate_blind_benchmark(findings)
    assert result.status == "completed"
    assert result.metrics is not None
    assert result.metrics["true_positive_count"] >= 1


def test_blind_cli_writes_skip_report(tmp_path, monkeypatch):
    monkeypatch.delenv(BLIND_SECRET_ENV, raising=False)
    monkeypatch.setattr("app.benchmark.blind.repo_benchmarks_root", lambda: tmp_path)
    from app.benchmark.blind import run_blind_benchmark_cli

    code = run_blind_benchmark_cli()
    assert code == 0
    report = json.loads((tmp_path / "reports" / "blind-benchmark.json").read_text(encoding="utf-8"))
    assert report["status"] == "skipped"
