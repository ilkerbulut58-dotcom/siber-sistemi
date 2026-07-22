"""Smoke baseline and deterministic Android fixture tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from app.benchmark.baseline import (
    SMOKE_BASELINE_NAME,
    compute_delta,
    load_baseline,
    load_smoke_baseline,
)


def _load_build_module():
    script = (
        Path(__file__).resolve().parents[2]
        / "benchmarks"
        / "fixtures"
        / "android-smoke"
        / "build_fixture_apk.py"
    )
    spec = importlib.util.spec_from_file_location("build_fixture_apk", script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_fixture_source_hash_is_stable():
    module = _load_build_module()
    first = module.fixture_source_hash()
    second = module.fixture_source_hash()
    assert first == second
    assert len(first) == 64


def test_apk_build_is_deterministic(tmp_path: Path):
    module = _load_build_module()
    out_a = tmp_path / "a.apk"
    out_b = tmp_path / "b.apk"
    sha_a, _ = module.build_apk(out_a)
    sha_b, _ = module.build_apk(out_b)
    assert sha_a == sha_b
    assert out_a.read_bytes() == out_b.read_bytes()


def test_smoke_baseline_file_exists_with_metadata():
    baseline = load_smoke_baseline()
    assert baseline is not None
    assert baseline["baseline_name"] == SMOKE_BASELINE_NAME
    assert baseline["baseline_type"] == "deterministic_smoke"
    assert baseline["fixture_version"] == "1.1.0"
    assert set(baseline["scope"]) == {"web-smoke", "api-smoke", "android-smoke"}
    assert "Does not represent general real-world product security accuracy" in baseline["description"]


def test_load_baseline_returns_suite_metrics():
    suite = load_baseline("web-smoke")
    assert suite is not None
    assert suite["baseline_name"] == SMOKE_BASELINE_NAME
    assert suite["true_positive_count"] == 7
    assert suite["confirmed_false_positive_count"] == 0
    assert suite["matcher_failure_count"] == 0


def test_compute_delta_includes_calibration_fields():
    baseline = load_baseline("web-smoke")
    assert baseline is not None
    delta = compute_delta(
        {
            "precision": 1.0,
            "recall": 1.0,
            "f1_score": 1.0,
            "false_negative_count": 0,
            "confirmed_false_positive_count": 0,
            "matcher_failure_count": 0,
            "duration_seconds": 0.4,
        },
        baseline,
    )
    assert delta["baseline_available"] is True
    assert delta["baseline_name"] == SMOKE_BASELINE_NAME
    assert delta["baseline_type"] == "deterministic_smoke"
    assert delta["baseline_run_id"] == baseline["run_id"]
    assert delta["precision_delta"] == pytest.approx(0.0)
    assert delta["recall_delta"] == pytest.approx(0.0)
    assert delta["f1_delta"] == pytest.approx(0.0)
    assert delta["new_false_negatives"] == 0
    assert delta["new_confirmed_false_positives"] == 0
    assert delta["matcher_failure_delta"] == 0


def test_baseline_fixture_source_hash_matches_build_script():
    module = _load_build_module()
    baseline = load_smoke_baseline()
    assert baseline is not None
    expected = module.fixture_source_hash()
    assert baseline["scanner_versions"]["fixture_source_hash"] == expected


def test_git_commit_prefers_github_sha_in_runner(monkeypatch):
    monkeypatch.setenv("GITHUB_SHA", "deadbeef" * 5)
    from app.benchmark.runner import _git_commit

    assert _git_commit() == "deadbeef" * 5
