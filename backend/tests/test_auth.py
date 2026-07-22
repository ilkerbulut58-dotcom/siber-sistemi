"""Authentication and organization endpoint tests."""

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str, password: str = "SecurePass123!") -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    assert response.status_code == 201
    return response.json()["data"]


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient) -> None:
    reg = await _register(client, "alice@example.com")
    assert reg["user"]["email"] == "alice@example.com"
    assert "access_token" in reg["tokens"]
    assert "email_verification_token" in reg

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "SecurePass123!"},
    )
    assert login.status_code == 200
    body = login.json()
    assert body["success"] is True
    assert body["data"]["tokens"]["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_duplicate_registration(client: AsyncClient) -> None:
    await _register(client, "dup@example.com")
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "SecurePass123!"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_EXISTS"


@pytest.mark.asyncio
async def test_auth_me_requires_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_verify_email(client: AsyncClient) -> None:
    reg = await _register(client, "verify@example.com")
    token = reg["email_verification_token"]
    response = await client.post("/api/v1/auth/verify-email", json={"token": token})
    assert response.status_code == 200
    assert response.json()["data"]["is_email_verified"] is True


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient) -> None:
    reg = await _register(client, "refresh@example.com")
    refresh = reg["tokens"]["refresh_token"]
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert response.status_code == 200
    assert response.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_create_and_list_organizations(client: AsyncClient) -> None:
    reg = await _register(client, "orgowner@example.com")
    headers = {"Authorization": f"Bearer {reg['tokens']['access_token']}"}

    create = await client.post(
        "/api/v1/organizations",
        json={"name": "Acme Security"},
        headers=headers,
    )
    assert create.status_code == 201
    org = create.json()["data"]
    assert org["name"] == "Acme Security"
    assert org["slug"] == "acme-security"

    listing = await client.get("/api/v1/organizations", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()["data"]) == 1


@pytest.mark.asyncio
async def test_invite_member(client: AsyncClient) -> None:
    owner = await _register(client, "owner@example.com")
    invitee = await _register(client, "member@example.com")
    headers = {"Authorization": f"Bearer {owner['tokens']['access_token']}"}

    org = (
        await client.post(
            "/api/v1/organizations",
            json={"name": "Invite Org"},
            headers=headers,
        )
    ).json()["data"]

    invite = await client.post(
        f"/api/v1/organizations/{org['id']}/members/invite",
        json={"email": "member@example.com", "role": "viewer"},
        headers=headers,
    )
    assert invite.status_code == 201
    assert invite.json()["data"]["email"] == "member@example.com"

    member_headers = {"Authorization": f"Bearer {invitee['tokens']['access_token']}"}
    members = await client.get(
        f"/api/v1/organizations/{org['id']}/members",
        headers=member_headers,
    )
    assert members.status_code == 200
    assert len(members.json()["data"]) == 2
