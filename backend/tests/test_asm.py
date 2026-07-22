"""Tests for Attack Surface Management (Phase 9)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.asm.risk import compute_asset_risk_score
from app.asm.types import DiscoveredAsset
from app.scanners.asm.cdn_waf_collector import detect_cdn_waf
from app.scanners.asm.dns_collector import collect_dns_records
from app.scanners.asm.tech_collector import detect_technologies
from app.services.asm_service import build_asset_fingerprint


def test_build_asset_fingerprint_stable() -> None:
    pid = uuid4()
    fp1 = build_asset_fingerprint(pid, "domain", "Example.COM")
    fp2 = build_asset_fingerprint(pid, "domain", "example.com")
    assert fp1 == fp2


def test_compute_asset_risk_from_metadata() -> None:
    score = compute_asset_risk_score(
        {
            "tls": {"valid": False, "error": "cert expired"},
            "http": {"security_headers": {"strict-transport-security": None}},
        },
        exposure_score=1.2,
        max_finding_risk=65.0,
        findings_count=2,
    )
    assert score >= 40.0
    assert score <= 100.0


def test_detect_cdn_waf_cloudflare() -> None:
    detected = detect_cdn_waf({"cf-ray": "abc123", "server": "cloudflare"})
    assert any(d["name"] == "Cloudflare" for d in detected)


def test_detect_technologies_from_headers() -> None:
    techs = detect_technologies({"server": "nginx/1.24.0", "x-powered-by": "PHP/8.2"})
    names = {t["name"] for t in techs}
    assert "nginx" in names or "PHP/8.2" in names


@pytest.mark.asyncio
async def test_discover_attack_surface_mocked() -> None:
    from app.scanners.asm.discovery import discover_attack_surface

    [
        DiscoveredAsset(
            asset_type="domain",
            identifier="example.com",
            url="https://example.com/",
            metadata={"dns": {"A": ["93.184.216.34"]}},
        )
    ]

    with patch(
        "app.scanners.asm.discovery.discover_subdomains",
        new_callable=AsyncMock,
        return_value=["example.com"],
    ), patch(
        "app.scanners.asm.discovery.collect_dns_records",
        return_value={"A": ["93.184.216.34"]},
    ), patch(
        "app.scanners.asm.discovery.probe_http",
        new_callable=AsyncMock,
        return_value={"reachable": True, "headers": {"server": "nginx"}, "security_headers": {}},
    ), patch(
        "app.scanners.asm.discovery.collect_tls_info",
        return_value={"valid": True, "days_until_expiry": 90},
    ):
        assets = await discover_attack_surface("https://example.com")

    assert len(assets) >= 1
    assert assets[0].identifier == "example.com"


def test_collect_dns_records_localhost_style(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeAnswer:
        def __init__(self, value: str) -> None:
            self._value = value

        def __str__(self) -> str:
            return self._value

    class FakeResolver:
        lifetime = 8.0

        def resolve(self, hostname: str, rtype: str):
            if rtype == "A":
                return [FakeAnswer("192.0.2.1")]
            raise Exception("no answer")

    monkeypatch.setattr("app.scanners.asm.dns_collector.dns.resolver.Resolver", lambda: FakeResolver())
    records = collect_dns_records("example.com")
    assert records.get("A") == ["192.0.2.1"]


async def _register_and_org(client) -> tuple[dict, dict, dict, dict]:
    email = f"asm-{uuid4().hex[:8]}@example.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePass123!", "full_name": "ASM Tester"},
    )
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['data']['tokens']['access_token']}"}
    org = (
        await client.post("/api/v1/organizations", json={"name": "ASM Org"}, headers=headers)
    ).json()["data"]
    project = (
        await client.post(
            f"/api/v1/organizations/{org['id']}/projects",
            json={"name": "ASM Project", "environment": "staging"},
            headers=headers,
        )
    ).json()["data"]
    domain = (
        await client.post(
            f"/api/v1/organizations/{org['id']}/projects/{project['id']}/domains",
            json={"hostname": "example.com", "method": "dns_txt"},
            headers=headers,
        )
    ).json()["data"]
    return headers, org, project, domain


@pytest.mark.asyncio
async def test_asm_discover_endpoint_does_not_500(client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SKIP_DOMAIN_VERIFICATION", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()
    headers, org, project, domain = await _register_and_org(client)

    with patch("app.api.v1.asm.dispatch_asm_discovery", new=AsyncMock()):
        resp = await client.post(
            f"/api/v1/organizations/{org['id']}/projects/{project['id']}/asm/discover",
            json={
                "domain_id": domain["id"],
                "target_url": "https://example.com",
                "authorization_accepted": True,
            },
            headers=headers,
        )

    assert resp.status_code != 500, resp.text
    body = resp.json()
    assert body["success"] is True
    assert resp.status_code == 201

