"""Verification engine deterministic URL cache tests."""

from __future__ import annotations

import pytest

from app.analysis import verification_engine
from app.analysis.types import CorrelatedFinding
from app.scanners.base import RawFinding

_PROXY = "https://benchmark-juice-proxy/"


def _header_finding(url: str) -> CorrelatedFinding:
    return CorrelatedFinding(
        correlation_key="missing-header-content-security-policy",
        title="Missing CSP",
        description="missing",
        severity="medium",
        affected_url=url,
        remediation=None,
        confidence="medium",
        evidence={},
        source_tools=["passive_http"],
        source_rule_ids=["missing-header-content-security-policy"],
        raw_sources=[
            RawFinding(
                source_tool="passive_http",
                source_rule_id="missing-header-content-security-policy",
                title="Missing CSP",
                description="missing",
                severity="medium",
                affected_url=url,
                evidence={"missing_header": "content-security-policy"},
                confidence="high",
            )
        ],
    )


@pytest.mark.asyncio
async def test_site_wide_header_verification_uses_scan_target_root(monkeypatch):
    requested_urls: list[str] = []

    class FakeResponse:
        def __init__(self, headers: dict[str, str]):
            self.headers = headers

    async def fake_get_response(url: str, cached_holder: dict):
        requested_urls.append(url)
        responses = cached_holder.setdefault("responses", {})
        canonical = verification_engine.canonicalize_url(url)
        if canonical not in responses:
            responses[canonical] = FakeResponse({})
        return responses[canonical]

    monkeypatch.setattr(verification_engine, "_get_response", fake_get_response)

    root = _PROXY
    robots = f"{_PROXY}robots.txt"
    permutations = [
        [_header_finding(robots), _header_finding(root)],
        [_header_finding(root), _header_finding(robots)],
    ]

    snapshots: list[tuple[tuple[str, str, str], ...]] = []
    for correlated in permutations:
        analyzed = await verification_engine.verify_findings(root, correlated)
        snapshots.append(
            tuple(
                sorted(
                    (item.affected_url, item.verified_confidence, item.verification_status)
                    for item in analyzed
                )
            )
        )

    assert snapshots[0] == snapshots[1]
    assert requested_urls
    assert all(url == root for url in requested_urls)
    assert all(item.verified_confidence in {"medium", "high"} for item in analyzed)
