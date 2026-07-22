"""Domain endpoint tests."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def _project_context(client: AsyncClient, email: str = "domain@example.com") -> tuple[dict, dict, dict]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePass123!", "full_name": "Domain User"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['data']['tokens']['access_token']}"}
    org = (
        await client.post("/api/v1/organizations", json={"name": "Domain Org"}, headers=headers)
    ).json()["data"]
    project = (
        await client.post(
            f"/api/v1/organizations/{org['id']}/projects",
            json={"name": "Main Site", "environment": "staging"},
            headers=headers,
        )
    ).json()["data"]
    return headers, org, project


@pytest.mark.asyncio
@patch("app.services.domain_service.hostname_resolves", return_value=True)
async def test_add_domain_and_instructions(_mock: AsyncMock, client: AsyncClient) -> None:
    headers, org, project = await _project_context(client)

    add = await client.post(
        f"/api/v1/organizations/{org['id']}/projects/{project['id']}/domains",
        json={"hostname": "example.com", "method": "dns_txt"},
        headers=headers,
    )
    assert add.status_code == 201
    domain = add.json()["data"]
    assert domain["hostname"] == "example.com"
    assert domain["is_verified"] is False

    instructions = await client.get(
        f"/api/v1/organizations/{org['id']}/projects/{project['id']}/domains/{domain['id']}/verification-instructions",
        headers=headers,
    )
    assert instructions.status_code == 200
    body = instructions.json()["data"]
    assert body["hostname"] == "example.com"
    assert len(body["instructions"]) >= 2


@pytest.mark.asyncio
@patch("app.services.domain_service.run_verification", new_callable=AsyncMock, return_value=True)
@patch("app.services.domain_service.hostname_resolves", return_value=True)
async def test_verify_domain(
    _resolve: AsyncMock,
    _verify: AsyncMock,
    client: AsyncClient,
) -> None:
    headers, org, project = await _project_context(client, "verify@example.com")

    domain = (
        await client.post(
            f"/api/v1/organizations/{org['id']}/projects/{project['id']}/domains",
            json={"hostname": "verify.example.com", "method": "dns_txt"},
            headers=headers,
        )
    ).json()["data"]

    response = await client.post(
        f"/api/v1/organizations/{org['id']}/projects/{project['id']}/domains/{domain['id']}/verify",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["verified"] is True
    assert body["domain"]["is_verified"] is True
