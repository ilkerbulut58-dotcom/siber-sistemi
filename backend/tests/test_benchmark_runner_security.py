"""Security tests for benchmark runner allowlists."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.benchmark.manifests import ALLOWED_SUITES, load_suite_manifest


def test_unknown_suite_rejected():
    with pytest.raises(ValueError):
        load_suite_manifest("evil-suite")


def test_allowlist_is_fixed():
    assert ALLOWED_SUITES == {"web-smoke", "api-smoke", "android-smoke"}


def test_web_smoke_manifest_loads():
    manifest = load_suite_manifest("web-smoke")
    assert manifest.suite == "web-smoke"
    assert manifest.targets[0].docker_services == ["benchmark-web"]
