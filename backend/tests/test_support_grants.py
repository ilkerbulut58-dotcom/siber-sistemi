"""Support grant access control tests."""

from __future__ import annotations

from uuid import UUID

from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import update

from app.core.database import async_session_factory
from app.models.user import User


async def _register(client: AsyncClient, email: str) -> dict:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePass123!", "full_name": email.split("@")[0]},
    )
    assert reg.status_code == 201
    return reg.json()["data"]


async def _make_platform_admin(user_id: str) -> None:
    async with async_session_factory() as session:
        await session.execute(
            update(User).where(User.id == UUID(user_id)).values(is_platform_admin=True)
        )
        await session.commit()


@pytest.mark.asyncio
async def test_support_grant_allows_viewer_access(client: AsyncClient):
    customer = await _register(client, "customer-grant@example.com")
    admin = await _register(client, "platform-grant@example.com")
    await _make_platform_admin(admin["user"]["id"])

    customer_headers = {"Authorization": f"Bearer {customer['tokens']['access_token']}"}
    admin_headers = {"Authorization": f"Bearer {admin['tokens']['access_token']}"}

    org = (
        await client.post(
            "/api/v1/organizations",
            json={"name": "Grant Test Org"},
            headers=customer_headers,
        )
    ).json()["data"]

    denied = await client.get(
        f"/api/v1/organizations/{org['id']}/projects",
        headers=admin_headers,
    )
    assert denied.status_code == 403

    grant = (
        await client.post(
            "/api/v1/platform/support-grants",
            json={
                "organization_id": org["id"],
                "granted_to_user_id": admin["user"]["id"],
                "reason": "Customer support ticket #12345",
                "duration_hours": 24,
            },
            headers=admin_headers,
        )
    ).json()["data"]
    assert grant["is_active"] is True

    allowed = await client.get(
        f"/api/v1/organizations/{org['id']}/projects",
        headers=admin_headers,
    )
    assert allowed.status_code == 200

    orgs = (await client.get("/api/v1/organizations", headers=admin_headers)).json()["data"]
    assert any(item["id"] == org["id"] for item in orgs)


@pytest.mark.asyncio
async def test_support_grant_viewer_cannot_mutate_findings(client: AsyncClient):
    customer = await _register(client, "customer-viewer@example.com")
    admin = await _register(client, "platform-viewer@example.com")
    await _make_platform_admin(admin["user"]["id"])

    customer_headers = {"Authorization": f"Bearer {customer['tokens']['access_token']}"}
    admin_headers = {"Authorization": f"Bearer {admin['tokens']['access_token']}"}

    org = (
        await client.post(
            "/api/v1/organizations",
            json={"name": "Viewer Grant Org"},
            headers=customer_headers,
        )
    ).json()["data"]
    project = (
        await client.post(
            f"/api/v1/organizations/{org['id']}/projects",
            json={"name": "P", "environment": "staging"},
            headers=customer_headers,
        )
    ).json()["data"]

    await client.post(
        "/api/v1/platform/support-grants",
        json={
            "organization_id": org["id"],
            "granted_to_user_id": admin["user"]["id"],
            "reason": "Read-only support access for investigation",
            "duration_hours": 8,
        },
        headers=admin_headers,
    )

    from app.models.finding import Finding, FindingStatus

    async with async_session_factory() as session:
        finding = Finding(
            organization_id=UUID(org["id"]),
            project_id=UUID(project["id"]),
            source_tool="test",
            source_rule_id="test-rule",
            title="Test finding",
            severity="low",
            status=FindingStatus.OPEN.value,
            asset_type="web",
            fingerprint="test-fingerprint-support-grant",
        )
        session.add(finding)
        await session.commit()
        finding_id = str(finding.id)

    patch = await client.patch(
        f"/api/v1/organizations/{org['id']}/findings/{finding_id}",
        json={"status": "resolved"},
        headers=admin_headers,
    )
    assert patch.status_code == 403


@pytest.mark.asyncio
async def test_revoked_support_grant_blocks_access(client: AsyncClient):
    customer = await _register(client, "customer-revoke@example.com")
    admin = await _register(client, "platform-revoke@example.com")
    await _make_platform_admin(admin["user"]["id"])

    customer_headers = {"Authorization": f"Bearer {customer['tokens']['access_token']}"}
    admin_headers = {"Authorization": f"Bearer {admin['tokens']['access_token']}"}

    org = (
        await client.post(
            "/api/v1/organizations",
            json={"name": "Revoke Org"},
            headers=customer_headers,
        )
    ).json()["data"]

    grant = (
        await client.post(
            "/api/v1/platform/support-grants",
            json={
                "organization_id": org["id"],
                "granted_to_user_id": admin["user"]["id"],
                "reason": "Temporary access for migration support",
                "duration_hours": 24,
            },
            headers=admin_headers,
        )
    ).json()["data"]

    revoke = await client.delete(
        f"/api/v1/platform/support-grants/{grant['id']}",
        headers=admin_headers,
    )
    assert revoke.status_code == 200

    blocked = await client.get(
        f"/api/v1/organizations/{org['id']}/projects",
        headers=admin_headers,
    )
    assert blocked.status_code == 403
