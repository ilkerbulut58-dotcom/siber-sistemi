"""Benchmark lab security guards — active profiles and suite isolation."""

from __future__ import annotations

import os

from app.benchmark.active_guard import active_scan_execution_allowed
from app.core.config import get_settings

ACTIVE_REALISTIC_SUITES = frozenset({"web-realistic-active", "api-realistic-active"})
BLOCKED_BENCHMARK_PROFILES = frozenset({"benchmark-active-web", "benchmark-active-api"})
REALISTIC_PASSIVE_SUITES = frozenset({"web-realistic-passive", "api-realistic-passive"})


def is_blocked_benchmark_profile(profile: str) -> bool:
    return profile in BLOCKED_BENCHMARK_PROFILES


def _active_lab_enabled() -> bool:
    settings = get_settings()
    return (
        settings.benchmark_active_realistic_enabled
        and os.environ.get("BENCHMARK_LAB_ISOLATED") == "true"
        and os.environ.get("BENCHMARK_LAB_CONTAINER_MODE") == "true"
    )


def assert_scan_profile_allowed(profile: str) -> None:
    """Reject benchmark-active scan profiles outside an authorized lab execution."""
    if not is_blocked_benchmark_profile(profile):
        return
    if active_scan_execution_allowed():
        return
    raise ValueError(
        f"Scan profile {profile!r} is restricted to the isolated benchmark lab"
    )


def assert_active_benchmark_create_allowed(profile: str, *, system_scope: bool) -> None:
    """Only hidden system-scope benchmark runs may create active benchmark scans."""
    if not is_blocked_benchmark_profile(profile):
        return
    if not system_scope:
        raise ValueError(
            f"Scan profile {profile!r} requires a system-scope benchmark workspace"
        )
    if not _active_lab_enabled():
        raise ValueError(
            f"Scan profile {profile!r} requires an isolated benchmark lab with phase 11.3 enabled"
        )
    if not active_scan_execution_allowed():
        raise ValueError(
            f"Scan profile {profile!r} requires an explicit benchmark active scan authorization"
        )


def assert_suite_runnable(suite: str) -> None:
    """Active realistic suites run only in the isolated Docker lab."""
    if suite not in ACTIVE_REALISTIC_SUITES:
        return
    if not _active_lab_enabled():
        raise ValueError(
            f"Suite {suite!r} requires BENCHMARK_LAB_ISOLATED=true, "
            "BENCHMARK_LAB_CONTAINER_MODE=true, and benchmark_active_realistic_enabled"
        )


def is_realistic_suite(suite: str) -> bool:
    return suite in REALISTIC_PASSIVE_SUITES or suite in ACTIVE_REALISTIC_SUITES
