"""Domain self-service authorization for security_analyst role."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.models.mixins import OrganizationRole


async def _owner_context(client: AsyncClient, email: str = "owner@example.com") -> tuple[dict, dict, dict]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePass123!", "full_name": "Owner User"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['data']['tokens']['access_token']}"}
    org = (
        await client.post("/api/v1/organizations", json={"name": "Analyst Org"}, headers=headers)
    ).json()["data"]
    project = (
        await client.post(
            f"/api/v1/organizations/{org['id']}/projects",
            json={"name": "Main Site", "environment": "staging"},
            headers=headers,
        )
    ).json()["data"]
    return headers, org, project


async def _invite_analyst(
    client: AsyncClient, owner_headers: dict, org_id: str, email: str = "analyst@example.com"
) -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePass123!", "full_name": "Analyst User"},
    )
    invite = await client.post(
        f"/api/v1/organizations/{org_id}/members/invite",
        json={"email": email, "role": OrganizationRole.SECURITY_ANALYST.value},
        headers=owner_headers,
    )
    assert invite.status_code == 201, invite.text
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePass123!"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["data"]["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _invite_viewer(
    client: AsyncClient, owner_headers: dict, org_id: str, email: str = "viewer@example.com"
) -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePass123!", "full_name": "Viewer User"},
    )
    invite = await client.post(
        f"/api/v1/organizations/{org_id}/members/invite",
        json={"email": email, "role": OrganizationRole.VIEWER.value},
        headers=owner_headers,
    )
    assert invite.status_code == 201, invite.text
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePass123!"},
    )
    token = login.json()["data"]["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
@patch("app.services.domain_service.hostname_resolves", return_value=True)
async def test_analyst_can_add_domain(_mock: AsyncMock, client: AsyncClient) -> None:
    owner_headers, org, project = await _owner_context(client, "owner-add@example.com")
    analyst_headers = await _invite_analyst(client, owner_headers, org["id"], "analyst-add@example.com")

    add = await client.post(
        f"/api/v1/organizations/{org['id']}/projects/{project['id']}/domains",
        json={"hostname": "analyst-owned.example.com", "method": "dns_txt"},
        headers=analyst_headers,
    )
    assert add.status_code == 201, add.text
    assert add.json()["data"]["hostname"] == "analyst-owned.example.com"


@pytest.mark.asyncio
@patch("app.services.domain_service.run_verification_detailed", new_callable=AsyncMock, return_value=(True, None))
@patch("app.services.domain_service.hostname_resolves", return_value=True)
async def test_analyst_can_verify_domain(
    _resolve: AsyncMock,
    _verify: AsyncMock,
    client: AsyncClient,
) -> None:
    owner_headers, org, project = await _owner_context(client, "owner-verify@example.com")
    analyst_headers = await _invite_analyst(client, owner_headers, org["id"], "analyst-verify@example.com")

    domain = (
        await client.post(
            f"/api/v1/organizations/{org['id']}/projects/{project['id']}/domains",
            json={"hostname": "verify-analyst.example.com", "method": "dns_txt"},
            headers=analyst_headers,
        )
    ).json()["data"]

    response = await client.post(
        f"/api/v1/organizations/{org['id']}/projects/{project['id']}/domains/{domain['id']}/verify",
        headers=analyst_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["verified"] is True


@pytest.mark.asyncio
@patch("app.services.domain_service.hostname_resolves", return_value=True)
async def test_viewer_cannot_add_domain(_mock: AsyncMock, client: AsyncClient) -> None:
    owner_headers, org, project = await _owner_context(client, "owner-viewer@example.com")
    viewer_headers = await _invite_viewer(client, owner_headers, org["id"], "viewer-add@example.com")

    add = await client.post(
        f"/api/v1/organizations/{org['id']}/projects/{project['id']}/domains",
        json={"hostname": "viewer-denied.example.com", "method": "dns_txt"},
        headers=viewer_headers,
    )
    assert add.status_code == 403


@pytest.mark.asyncio
@patch("app.services.domain_service.hostname_resolves", return_value=True)
async def test_analyst_cannot_approve_active_scan(_mock: AsyncMock, client: AsyncClient) -> None:
    owner_headers, org, project = await _owner_context(client, "owner-approve@example.com")
    analyst_headers = await _invite_analyst(client, owner_headers, org["id"], "analyst-approve@example.com")

    domain = (
        await client.post(
            f"/api/v1/organizations/{org['id']}/projects/{project['id']}/domains",
            json={"hostname": "approve-denied.example.com", "method": "dns_txt"},
            headers=owner_headers,
        )
    ).json()["data"]

    response = await client.post(
        f"/api/v1/organizations/{org['id']}/projects/{project['id']}/domains/{domain['id']}/approve-active-scan",
        headers=analyst_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_analyst_cannot_update_organization(client: AsyncClient) -> None:
    owner_headers, org, _project = await _owner_context(client, "owner-patch@example.com")
    analyst_headers = await _invite_analyst(client, owner_headers, org["id"], "analyst-patch@example.com")

    response = await client.patch(
        f"/api/v1/organizations/{org['id']}",
        json={"name": "Renamed"},
        headers=analyst_headers,
    )
    assert response.status_code == 403
