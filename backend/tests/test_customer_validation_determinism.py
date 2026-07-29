"""Order-independent customer-visible validation determinism tests."""

from __future__ import annotations

import json
import random

import pytest

from app.benchmark.customer_validation import (
    CustomerVisibility,
    build_customer_validation_artifact,
    canonical_validation_snapshot,
)
from app.scanners.base import RawFinding

_PROXY = "https://benchmark-juice-proxy/"


def _passive_csp(url: str = _PROXY) -> RawFinding:
    return RawFinding(
        source_tool="passive_http",
        source_rule_id="missing-header-content-security-policy",
        title="Missing Content-Security-Policy header",
        description="missing",
        severity="medium",
        affected_url=url,
        evidence={"missing_header": "content-security-policy"},
        confidence="high",
    )


def _passive_hsts(url: str = _PROXY) -> RawFinding:
    return RawFinding(
        source_tool="passive_http",
        source_rule_id="missing-header-strict-transport-security",
        title="Missing Strict-Transport-Security header",
        description="missing",
        severity="medium",
        affected_url=url,
        evidence={"missing_header": "strict-transport-security"},
        confidence="high",
    )


def _passive_xcto(url: str = _PROXY) -> RawFinding:
    return RawFinding(
        source_tool="passive_http",
        source_rule_id="missing-header-x-content-type-options",
        title="Missing X-Content-Type-Options header",
        description="missing",
        severity="low",
        affected_url=url,
        evidence={"missing_header": "x-content-type-options"},
        confidence="high",
    )


def _zap_header(rule_suffix: str, url: str, *, confidence: str = "low") -> RawFinding:
    return RawFinding(
        source_tool="zap",
        source_rule_id=f"missing-header-{rule_suffix}",
        title=f"Missing {rule_suffix}",
        description="zap",
        severity="medium",
        affected_url=url,
        confidence=confidence,
        evidence={"dedup_fingerprint": f"zap-{rule_suffix}-{url}"},
    )


def _zap_x_powered_by(url: str, *, confidence: str = "low") -> RawFinding:
    return RawFinding(
        source_tool="zap",
        source_rule_id="x-powered-by-disclosure",
        title="X-Powered-By disclosure",
        description="zap",
        severity="info",
        affected_url=url,
        confidence=confidence,
    )


def _passive_x_powered_by(url: str = _PROXY) -> RawFinding:
    return RawFinding(
        source_tool="passive_http",
        source_rule_id="x-powered-by-disclosure",
        title="X-Powered-By disclosure",
        description="disclosure",
        severity="info",
        affected_url=url,
        evidence={"x_powered_by": "Express"},
        confidence="high",
    )


def _passive_server(url: str = _PROXY) -> RawFinding:
    return RawFinding(
        source_tool="passive_http",
        source_rule_id="server-disclosure",
        title="Server version disclosure",
        description="disclosure",
        severity="info",
        affected_url=url,
        evidence={"server": "nginx/1.18"},
        confidence="high",
    )


def _run7fff515b_like_findings() -> list[RawFinding]:
    """Reconstruct the unstable run: passive root findings plus ZAP URL noise."""
    robots = f"{_PROXY}robots.txt"
    ftp = f"{_PROXY}ftp"
    return [
        _passive_csp(),
        _passive_hsts(),
        _passive_xcto(),
        _passive_server(),
        _passive_x_powered_by(),
        _zap_header("strict-transport-security", _PROXY),
        _zap_header("content-security-policy", ftp),
        _zap_header("x-content-type-options", robots),
        _zap_x_powered_by(robots),
        _zap_header("strict-transport-security", robots),
        _zap_header("x-content-type-options", _PROXY),
    ]


def _run5d7eaec4_like_findings() -> list[RawFinding]:
    """Same finding set as the unstable run, different discovery order."""
    return list(reversed(_run7fff515b_like_findings()))


@pytest.mark.parametrize(
    "findings_factory",
    [
        _run7fff515b_like_findings,
        _run5d7eaec4_like_findings,
    ],
)
def test_site_wide_header_groups_stable_across_input_orders(findings_factory):
    baseline = canonical_validation_snapshot(findings_factory())
    permutations = [
        findings_factory(),
        list(reversed(findings_factory())),
    ]
    rng = random.Random(42)
    shuffled = findings_factory()
    for _ in range(18):
        rng.shuffle(shuffled)
        permutations.append(list(shuffled))

    for ordered in permutations:
        assert canonical_validation_snapshot(ordered) == baseline


def test_run7fff515b_and_run5d7eaec4_produce_same_customer_visible_snapshot():
    """Regression for CI nondeterminism: passive root evidence must dominate URL noise."""
    assert canonical_validation_snapshot(_run7fff515b_like_findings()) == canonical_validation_snapshot(
        _run5d7eaec4_like_findings()
    )


def test_site_wide_merge_confirms_passive_csp_even_with_zap_url_noise():
    artifact = build_customer_validation_artifact(_run7fff515b_like_findings())
    csp_views = [view for view in artifact.findings if view.source_rule_id.endswith("content-security-policy")]
    assert len(csp_views) == 1
    assert csp_views[0].visibility == CustomerVisibility.CONFIRMED
    assert csp_views[0].affected_url == _PROXY


def test_site_wide_validation_count_is_order_independent():
    baseline_count = build_customer_validation_artifact(_run7fff515b_like_findings()).customer_visible_count
    shuffled = _run7fff515b_like_findings()
    random.Random(99).shuffle(shuffled)
    assert build_customer_validation_artifact(shuffled).customer_visible_count == baseline_count


@pytest.mark.parametrize(
    "url_variant",
    [
        _PROXY,
        "https://benchmark-juice-proxy",
        "HTTPS://Benchmark-Juice-Proxy/",
        "https://benchmark-juice-proxy:443/",
    ],
)
def test_url_variants_do_not_change_customer_visible_snapshot(url_variant: str):
    baseline = canonical_validation_snapshot([_passive_csp(_PROXY), _passive_hsts(_PROXY)])
    variant = canonical_validation_snapshot([_passive_csp(url_variant), _passive_hsts(url_variant)])
    assert variant == baseline


def test_duplicate_urls_do_not_change_customer_visible_snapshot():
    findings = [_passive_csp(_PROXY), _passive_csp(_PROXY), _passive_hsts(_PROXY)]
    assert canonical_validation_snapshot(findings) == canonical_validation_snapshot(
        [_passive_csp(_PROXY), _passive_hsts(_PROXY)]
    )


def test_canonical_snapshot_is_json_stable():
    snapshot = canonical_validation_snapshot(_run7fff515b_like_findings())
    encoded = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    assert '"customer_visible_count":' in encoded
    assert snapshot["customer_visible_count"] > 0
