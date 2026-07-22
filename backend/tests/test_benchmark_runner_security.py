"""Security tests for benchmark runner allowlists."""

from __future__ import annotations

import pytest

from app.benchmark.manifests import ALLOWED_SUITES, load_suite_manifest


def test_unknown_suite_rejected():
    with pytest.raises(ValueError):
        load_suite_manifest("evil-suite")


def test_allowlist_includes_realistic_passive():
    assert {"web-smoke", "api-smoke", "android-smoke"}.issubset(ALLOWED_SUITES)
    assert "web-realistic-passive" in ALLOWED_SUITES
    assert "api-realistic-passive" in ALLOWED_SUITES


def test_web_smoke_manifest_loads():
    manifest = load_suite_manifest("web-smoke")
    assert manifest.suite == "web-smoke"
    assert manifest.targets[0].docker_services == ["benchmark-web"]
