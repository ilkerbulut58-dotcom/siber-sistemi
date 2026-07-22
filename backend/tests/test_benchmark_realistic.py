"""Phase 11.1 realistic passive benchmark tests."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.benchmark.baseline import (
    REALISTIC_BASELINE_NAME,
    REALISTIC_BASELINE_V11_NAME,
    load_baseline,
    load_realistic_baseline,
    load_realistic_baseline_v11,
)
from app.benchmark.fixtures import (
    BenchmarkFixture,
    ExpectedFindingFixture,
    load_fixture,
    load_subset,
)
from app.benchmark.manifests import (
    ALLOWED_SUITES,
    ALLOWED_TARGET_HOSTS,
    REALISTIC_PASSIVE_SUITES,
    load_suite_manifest,
)
from app.benchmark.security import assert_scan_profile_allowed, assert_suite_runnable
from app.core.config import get_settings
from app.services.benchmark_matching_service import match_findings


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _expected(key: str, *, support: str = "supported", required: bool = True):
    return SimpleNamespace(
        id=uuid4(),
        expected_key=key,
        accepted_alternative_keys=[],
        category=key,
        affected_location=None,
        detection_required=required,
        automation_support=support,
    )


def _finding(*, key: str):
    return SimpleNamespace(
        id=uuid4(),
        correlation_key=key,
        source_rule_id=key,
        fingerprint="abc",
        affected_url=None,
        title="finding",
    )


def test_automation_support_defaults_supported():
    item = ExpectedFindingFixture(
        expected_key="missing-csp",
        title="CSP",
        severity="medium",
    )
    assert item.automation_support == "supported"


def test_supported_metrics_exclude_manual_only_and_partial():
    records, metrics = match_findings(
        [
            _expected("supported-hit", support="supported"),
            _expected("supported-miss", support="supported"),
            _expected("partial-hit", support="partially_supported"),
            _expected("manual-gap", support="manual_only", required=False),
            _expected("unsupported-gap", support="unsupported", required=False),
        ],
        [_finding(key="supported-hit"), _finding(key="partial-hit")],
    )
    assert metrics.expected_count == 2
    assert metrics.true_positive_count == 1
    assert metrics.false_negative_count == 1
    assert metrics.partial_true_positive_count == 1
    assert metrics.partial_recall == 1.0
    assert metrics.owasp_coverage_gap_count == 2
    assert any(record.classification == "true_positive" for record in records)


def test_active_suite_blocked_without_lab_env():
    get_settings.cache_clear()
    with pytest.raises(ValueError, match="requires"):
        assert_suite_runnable("web-realistic-active")
    with pytest.raises(ValueError, match="requires"):
        assert_suite_runnable("api-realistic-active")


def test_blocked_scan_profiles_rejected():
    with pytest.raises(ValueError, match="restricted"):
        assert_scan_profile_allowed("benchmark-active-web")
    with pytest.raises(ValueError, match="restricted"):
        assert_scan_profile_allowed("benchmark-active-api")


def test_realistic_allowlist_hosts():
    manifest = load_suite_manifest("web-realistic-passive")
    assert manifest.targets[0].target_url == "https://benchmark-juice-proxy/"
    assert "benchmark-juice-proxy" in ALLOWED_TARGET_HOSTS
    assert REALISTIC_PASSIVE_SUITES <= ALLOWED_SUITES


def test_pinned_digest_lock_file_parse():
    lock_path = _repo_root() / "benchmarks" / "docker" / "images.lock.json"
    payload = json.loads(lock_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    for name, entry in payload["images"].items():
        assert "PLACEHOLDER" not in entry["digest"], name
        assert entry["tag"] != "latest", name
        assert entry["digest"].startswith("sha256:")


def test_smoke_baseline_hash_unchanged():
    import subprocess

    blob = subprocess.check_output(
        ["git", "rev-parse", "HEAD:benchmarks/baselines/smoke-v1.1.0.json"],
        cwd=_repo_root(),
        text=True,
    ).strip()
    assert blob == "d9869852b09d09e5e35cae9e1e891058ce0a68a9"


def test_subset_manifest_max_five():
    root = _repo_root() / "benchmarks"
    subset = load_subset(root / "fixtures/web-realistic-passive/subset-main.yaml", fixtures_root=root)
    assert len(subset.expected_keys) <= 5
    assert len(subset.expected_keys) == 5


def test_realistic_manifest_loads():
    manifest = load_suite_manifest("api-realistic-passive")
    assert manifest.suite == "api-realistic-passive"
    assert manifest.targets[0].health_url == "https://benchmark-crapi-proxy/health"


def test_active_manifest_is_enabled():
    manifest = load_suite_manifest("web-realistic-active")
    assert manifest.blocked is False
    assert manifest.targets[0].scan_profile == "benchmark-active-web"


def test_fixture_loader_accepts_automation_support():
    root = _repo_root() / "benchmarks"
    fixture = load_fixture(root / "fixtures/web-realistic-passive/ground-truth.yaml", fixtures_root=root)
    assert isinstance(fixture, BenchmarkFixture)
    assert fixture.expected_findings[0].automation_support == "supported"


def test_container_mode_skips_docker_lifecycle(monkeypatch):
    from app.benchmark import docker_control

    monkeypatch.setenv("BENCHMARK_LAB_CONTAINER_MODE", "true")
    docker_control.start_services(["benchmark-juice-proxy"], realistic=True)
    docker_control.stop_services(["benchmark-juice-proxy"], realistic=True)


def test_realistic_baseline_file_metadata():
    baseline = load_realistic_baseline()
    assert baseline is not None
    assert baseline["baseline_name"] == REALISTIC_BASELINE_NAME
    assert baseline["baseline_type"] == "realistic_pinned_passive"
    desc = baseline["description"]
    assert "Does not represent general product security accuracy" in desc
    assert "Juice Shop and crAPI passive" in desc
    assert "regression protection" in desc
    assert baseline["fixture_version"] == "1.0.0"
    assert set(baseline["scope"]) == {"web-realistic-passive", "api-realistic-passive"}


def test_load_realistic_baseline_v10_suite_metrics():
    baseline = load_realistic_baseline()
    assert baseline is not None
    web = baseline["suites"]["web-realistic-passive"]
    api = baseline["suites"]["api-realistic-passive"]
    assert web["true_positive_count"] == 3
    assert web["confirmed_false_positive_count"] == 1
    assert api["confirmed_false_positive_count"] == 3
    assert api["precision"] == 0.5


def test_load_realistic_baseline_v11_metadata():
    baseline = load_realistic_baseline_v11()
    assert baseline is not None
    assert baseline["baseline_name"] == REALISTIC_BASELINE_V11_NAME
    assert baseline["baseline_type"] == "realistic_pinned_passive"
    assert "Does not represent general product security accuracy" in baseline["description"]
    assert baseline["scanner_versions"]["zap"] == "2.17.0"
    assert baseline["scanner_versions"]["nuclei_version"] == "3.3.7"
    assert baseline["scanner_versions"]["nuclei_template_allowlist_hash"]


def test_load_realistic_baseline_suite_metrics():
    web = load_baseline("web-realistic-passive")
    api = load_baseline("api-realistic-passive")
    assert web is not None
    assert api is not None
    assert web["baseline_name"] == REALISTIC_BASELINE_V11_NAME
    assert web["true_positive_count"] == 3
    assert web["false_negative_count"] == 2
    assert web["confirmed_false_positive_count"] == 3
    assert web["partial_recall"] == 0.0
    assert web["owasp_coverage_gap_count"] == 2
    assert api["confirmed_false_positive_count"] == 2
    assert api["precision"] == 0.6
    assert web["scanner_metrics"]["zap"]["finding_count"] == 8
    assert api["scanner_metrics"]["nuclei"]["finding_count"] == 10


def test_images_lock_includes_zap_and_nuclei():
    lock_path = _repo_root() / "benchmarks" / "docker" / "images.lock.json"
    payload = json.loads(lock_path.read_text(encoding="utf-8"))
    images = payload["images"]
    assert "zaproxy-stable" in images
    assert images["zaproxy-stable"]["digest"].startswith("sha256:")
    assert "nuclei" in images
    assert images["nuclei"]["tag"] == "3.3.7"


def test_realistic_compose_pins_zap_daemon():
    compose = (_repo_root() / "docker-compose.realistic.yml").read_text(encoding="utf-8")
    lock = json.loads(
        (_repo_root() / "benchmarks" / "docker" / "images.lock.json").read_text(encoding="utf-8")
    )
    zap_digest = lock["images"]["zaproxy-stable"]["digest"]
    assert "benchmark-zap:" in compose
    assert zap_digest in compose
    assert "ZAP_API_URL: http://benchmark-zap:8080" in compose
    assert "ZAP_ENABLED: \"true\"" in compose


@pytest.mark.asyncio
async def test_collect_lab_scanner_versions_without_zap(monkeypatch):
    from app.benchmark.scanner_versions import collect_lab_scanner_versions

    monkeypatch.setenv("ZAP_ENABLED", "false")
    get_settings.cache_clear()
    versions = await collect_lab_scanner_versions()
    get_settings.cache_clear()
    assert versions["app"]
    assert versions["zap"] == "disabled"
    assert versions["zap_image_digest"].startswith("sha256:")
    assert versions["nuclei_version"] == "3.3.7"
