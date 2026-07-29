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
async def test_verify_findings_uses_distinct_cached_responses_per_url(monkeypatch):
    requested_urls: list[str] = []

    class FakeResponse:
        def __init__(self, headers: dict[str, str]):
            self.headers = headers

    async def fake_get_response(url: str, cached_holder: dict):
        requested_urls.append(url)
        responses = cached_holder.setdefault("responses", {})
        canonical = verification_engine.canonicalize_url(url)
        if canonical not in responses:
            if canonical.endswith("/robots.txt"):
                responses[canonical] = FakeResponse({"content-security-policy": "default-src 'self'"})
            else:
                responses[canonical] = FakeResponse({})
        return responses[canonical]

    monkeypatch.setattr(verification_engine, "_get_response", fake_get_response)

    root = _PROXY
    robots = f"{_PROXY}robots.txt"
    analyzed = await verification_engine.verify_findings(
        root,
        [_header_finding(robots), _header_finding(root)],
    )

    assert requested_urls == [robots, root]
    by_url = {item.affected_url: item.verified_confidence for item in analyzed}
    assert by_url[root] in {"medium", "high"}
    assert by_url[robots] == "low"
