"""Project endpoint tests."""

import pytest
from httpx import AsyncClient


async def _auth_context(client: AsyncClient, email: str = "proj@example.com") -> tuple[dict, dict]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePass123!", "full_name": "Proj User"},
    )
    assert reg.status_code == 201
    data = reg.json()["data"]
    headers = {"Authorization": f"Bearer {data['tokens']['access_token']}"}
    org = (
        await client.post(
            "/api/v1/organizations",
            json={"name": "Proj Org"},
            headers=headers,
        )
    ).json()["data"]
    return headers, org


@pytest.mark.asyncio
async def test_create_and_list_projects(client: AsyncClient) -> None:
    headers, org = await _auth_context(client)

    create = await client.post(
        f"/api/v1/organizations/{org['id']}/projects",
        json={"name": "Web App", "environment": "staging"},
        headers=headers,
    )
    assert create.status_code == 201
    project = create.json()["data"]
    assert project["name"] == "Web App"
    assert project["environment"] == "staging"

    listing = await client.get(
        f"/api/v1/organizations/{org['id']}/projects",
        headers=headers,
    )
    assert listing.status_code == 200
    assert len(listing.json()["data"]) == 1


@pytest.mark.asyncio
async def test_get_project(client: AsyncClient) -> None:
    headers, org = await _auth_context(client, "getproj@example.com")
    project = (
        await client.post(
            f"/api/v1/organizations/{org['id']}/projects",
            json={"name": "API Gateway"},
            headers=headers,
        )
    ).json()["data"]

    response = await client.get(
        f"/api/v1/organizations/{org['id']}/projects/{project['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "API Gateway"
