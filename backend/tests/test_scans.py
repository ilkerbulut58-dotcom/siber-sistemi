"""Scan endpoint tests."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def _verified_domain(client: AsyncClient, email: str = "scan@example.com") -> tuple[dict, dict, dict]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePass123!", "full_name": "Scan User"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['data']['tokens']['access_token']}"}
    org = (
        await client.post("/api/v1/organizations", json={"name": "Scan Org"}, headers=headers)
    ).json()["data"]
    project = (
        await client.post(
            f"/api/v1/organizations/{org['id']}/projects",
            json={"name": "Scan Target", "environment": "staging"},
            headers=headers,
        )
    ).json()["data"]

    with patch("app.services.domain_service.hostname_resolves", return_value=True):
        domain = (
            await client.post(
                f"/api/v1/organizations/{org['id']}/projects/{project['id']}/domains",
                json={"hostname": "scan.example.com", "method": "dns_txt"},
                headers=headers,
            )
        ).json()["data"]

    with patch("app.services.domain_service.run_verification", new_callable=AsyncMock, return_value=True):
        await client.post(
            f"/api/v1/organizations/{org['id']}/projects/{project['id']}/domains/{domain['id']}/verify",
            headers=headers,
        )

    return headers, org, {"project": project, "domain": domain}


@pytest.mark.asyncio
async def test_list_scan_profiles(client: AsyncClient) -> None:
    headers, _, _ = await _verified_domain(client, "profiles@example.com")
    response = await client.get("/api/v1/scan-profiles", headers=headers)
    assert response.status_code == 200
    profiles = response.json()["data"]
    assert len(profiles) == 3
    assert {p["name"] for p in profiles} == {"safe", "deep", "code"}


@pytest.mark.asyncio
async def test_start_scan_requires_authorization(client: AsyncClient) -> None:
    headers, org, ctx = await _verified_domain(client, "noauth@example.com")
    response = await client.post(
        f"/api/v1/organizations/{org['id']}/scans",
        json={
            "project_id": ctx["project"]["id"],
            "domain_id": ctx["domain"]["id"],
            "scan_profile": "safe",
            "target_url": "https://scan.example.com",
            "authorization_accepted": False,
        },
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "AUTHORIZATION_REQUIRED"


@pytest.mark.asyncio
async def test_start_safe_scan(client: AsyncClient) -> None:
    headers, org, ctx = await _verified_domain(client)
    response = await client.post(
        f"/api/v1/organizations/{org['id']}/scans",
        json={
            "project_id": ctx["project"]["id"],
            "domain_id": ctx["domain"]["id"],
            "scan_profile": "safe",
            "target_url": "https://scan.example.com",
            "authorization_accepted": True,
        },
        headers=headers,
    )
    assert response.status_code == 201
    scan = response.json()["data"]
    assert scan["status"] == "queued"
    assert scan["scan_profile"] == "safe"

    listing = await client.get(f"/api/v1/organizations/{org['id']}/scans", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()["data"]) == 1
