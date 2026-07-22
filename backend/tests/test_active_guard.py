"""Security tests for active benchmark guards (phase 11.3)."""

from __future__ import annotations

import pytest

from app.benchmark.active_guard import (
    ActiveBenchmarkGuard,
    ActiveBenchmarkGuardError,
    guard_for_profile,
    load_api_active_allowlist,
    load_web_active_allowlist,
)
from app.benchmark.security import (
    assert_active_benchmark_create_allowed,
    assert_scan_profile_allowed,
    assert_suite_runnable,
)
from app.core.config import get_settings


@pytest.fixture
def active_lab_env(monkeypatch):
    monkeypatch.setenv("BENCHMARK_LAB_ISOLATED", "true")
    monkeypatch.setenv("BENCHMARK_LAB_CONTAINER_MODE", "true")
    monkeypatch.setenv("BENCHMARK_ACTIVE_REALISTIC_ENABLED", "true")
    monkeypatch.setenv("BENCHMARK_ACTIVE_SCAN_ALLOWED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_active_suite_blocked_without_lab_env():
    get_settings.cache_clear()
    with pytest.raises(ValueError, match="requires"):
        assert_suite_runnable("web-realistic-active")


def test_active_suite_allowed_in_lab(active_lab_env):
    assert_suite_runnable("web-realistic-active")
    assert_suite_runnable("api-realistic-active")


def test_blocked_scan_profiles_rejected_outside_lab():
    get_settings.cache_clear()
    with pytest.raises(ValueError, match="restricted"):
        assert_scan_profile_allowed("benchmark-active-web")


def test_active_scan_profile_allowed_in_lab_execution(active_lab_env):
    assert_scan_profile_allowed("benchmark-active-web")
    assert_scan_profile_allowed("benchmark-active-api")


def test_active_create_requires_system_scope(active_lab_env):
    with pytest.raises(ValueError, match="system-scope"):
        assert_active_benchmark_create_allowed("benchmark-active-web", system_scope=False)


def test_active_create_allowed_for_system_scope(active_lab_env):
    assert_active_benchmark_create_allowed("benchmark-active-web", system_scope=True)


def test_allowlist_accepts_fixture_hosts():
    guard = ActiveBenchmarkGuard(load_web_active_allowlist())
    guard.validate_target_url("https://benchmark-juice-proxy/")
    guard.validate_request(url="https://benchmark-juice-proxy/", method="GET")


def test_external_ip_blocked(active_lab_env):
    guard = guard_for_profile("benchmark-active-web")
    with pytest.raises(ActiveBenchmarkGuardError, match="External IP"):
        guard.validate_target_url("https://8.8.8.8/")


def test_metadata_endpoint_blocked(active_lab_env):
    guard = guard_for_profile("benchmark-active-api")
    with pytest.raises(ActiveBenchmarkGuardError, match="Metadata"):
        guard.validate_target_url("https://169.254.169.254/latest/meta-data/")


def test_destructive_endpoint_blocked(active_lab_env):
    guard = guard_for_profile("benchmark-active-web")
    with pytest.raises(ActiveBenchmarkGuardError, match="Destructive"):
        guard.validate_request(url="https://benchmark-juice-proxy/rest/user/login", method="POST")


def test_delete_method_blocked(active_lab_env):
    guard = guard_for_profile("benchmark-active-api")
    with pytest.raises(ActiveBenchmarkGuardError, match="Destructive"):
        guard.validate_request(url="https://benchmark-crapi-proxy/health", method="DELETE")


def test_redirect_payload_blocked(active_lab_env):
    guard = guard_for_profile("benchmark-active-web")
    with pytest.raises(ActiveBenchmarkGuardError, match="Redirect"):
        guard.validate_request(
            url="https://benchmark-juice-proxy/redirect?next=https://evil.example/",
            method="GET",
        )


def test_request_budget_enforced(active_lab_env, monkeypatch):
    monkeypatch.setenv("BENCHMARK_ACTIVE_REQUEST_BUDGET", "1")
    get_settings.cache_clear()
    guard = guard_for_profile("benchmark-active-web")
    guard.validate_request(url="https://benchmark-juice-proxy/", method="GET")
    with pytest.raises(ActiveBenchmarkGuardError, match="budget exhausted"):
        guard.validate_request(url="https://benchmark-juice-proxy/api/products", method="GET")


def test_kill_switch_blocks_requests(active_lab_env, monkeypatch):
    monkeypatch.setenv("BENCHMARK_ACTIVE_KILL_SWITCH", "true")
    guard = guard_for_profile("benchmark-active-web")
    with pytest.raises(ActiveBenchmarkGuardError, match="kill switch"):
        guard.validate_target_url("https://benchmark-juice-proxy/")


def test_active_manifests_unblocked():
    from app.benchmark.manifests import load_suite_manifest

    web = load_suite_manifest("web-realistic-active")
    api = load_suite_manifest("api-realistic-active")
    assert web.blocked is False
    assert api.blocked is False
    assert web.targets[0].blocked is False
    assert web.targets[0].scan_profile == "benchmark-active-web"
