"""Benchmark lab security guards — active profiles and suite isolation."""

from __future__ import annotations

import os

from app.core.config import get_settings

ACTIVE_REALISTIC_SUITES = frozenset({"web-realistic-active", "api-realistic-active"})
BLOCKED_BENCHMARK_PROFILES = frozenset({"benchmark-active-web", "benchmark-active-api"})
REALISTIC_PASSIVE_SUITES = frozenset({"web-realistic-passive", "api-realistic-passive"})


def assert_scan_profile_allowed(profile: str) -> None:
    """Reject benchmark-active scan profiles outside the isolated lab."""
    if profile in BLOCKED_BENCHMARK_PROFILES:
        raise ValueError(
            f"Scan profile {profile!r} is restricted to the isolated benchmark lab"
        )


def assert_suite_runnable(suite: str) -> None:
    """Active realistic suites remain blocked until phase 11.3."""
    if suite not in ACTIVE_REALISTIC_SUITES:
        return
    settings = get_settings()
    if not settings.benchmark_active_realistic_enabled:
        raise ValueError(
            f"Suite {suite!r} is blocked: active realistic benchmarks require phase 11.3"
        )
    if os.environ.get("BENCHMARK_LAB_ISOLATED") != "true":
        raise ValueError(
            f"Suite {suite!r} requires BENCHMARK_LAB_ISOLATED=true in a closed Docker lab"
        )
    if os.environ.get("BENCHMARK_LAB_CONTAINER_MODE") != "true":
        raise ValueError(
            f"Suite {suite!r} requires BENCHMARK_LAB_CONTAINER_MODE=true on the internal network"
        )


def is_realistic_suite(suite: str) -> bool:
    return suite in REALISTIC_PASSIVE_SUITES or suite in ACTIVE_REALISTIC_SUITES
