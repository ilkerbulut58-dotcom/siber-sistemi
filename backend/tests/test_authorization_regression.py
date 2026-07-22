"""Authorization regression tests for organization isolation and support grants."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update

from app.core.database import async_session_factory
from app.models.organization import Organization
from app.models.support_grant import OrganizationSupportGrant
from app.models.user import User
from app.services.benchmark_workspace_service import BENCHMARK_ORG_SLUG, BenchmarkWorkspaceService


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


def _headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _create_org(client: AsyncClient, headers: dict[str, str], name: str) -> dict:
    resp = await client.post("/api/v1/organizations", json={"name": name}, headers=headers)
    assert resp.status_code == 201
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_normal_user_sees_own_organization(client: AsyncClient) -> None:
    user = await _register(client, f"owner-{uuid4().hex[:6]}@example.com")
    headers = _headers(user["tokens"])
    org = await _create_org(client, headers, "My Organization")

    orgs = (await client.get("/api/v1/organizations", headers=headers)).json()["data"]
    assert any(item["id"] == org["id"] for item in orgs)

    detail = await client.get(f"/api/v1/organizations/{org['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["data"]["id"] == org["id"]


@pytest.mark.asyncio
async def test_normal_user_cannot_see_system_scope_organization(client: AsyncClient) -> None:
    async with async_session_factory() as db:
        await BenchmarkWorkspaceService(db).ensure_workspace()
        system_org_id = (
            await db.execute(select(Organization).where(Organization.slug == BENCHMARK_ORG_SLUG))
        ).scalar_one().id
        await db.commit()

    user = await _register(client, f"user-{uuid4().hex[:6]}@example.com")
    headers = _headers(user["tokens"])

    orgs = (await client.get("/api/v1/organizations", headers=headers)).json()["data"]
    assert all(item["id"] != str(system_org_id) for item in orgs)

    detail = await client.get(f"/api/v1/organizations/{system_org_id}", headers=headers)
    assert detail.status_code == 404


@pytest.mark.asyncio
async def test_normal_user_cannot_access_other_customer_organization(client: AsyncClient) -> None:
    owner_a = await _register(client, f"customer-a-{uuid4().hex[:6]}@example.com")
    owner_b = await _register(client, f"customer-b-{uuid4().hex[:6]}@example.com")

    org_a = await _create_org(client, _headers(owner_a["tokens"]), "Customer A Org")
    headers_b = _headers(owner_b["tokens"])

    orgs = (await client.get("/api/v1/organizations", headers=headers_b)).json()["data"]
    assert all(item["id"] != org_a["id"] for item in orgs)

    detail = await client.get(f"/api/v1/organizations/{org_a['id']}", headers=headers_b)
    assert detail.status_code in (403, 404)

    projects = await client.get(
        f"/api/v1/organizations/{org_a['id']}/projects",
        headers=headers_b,
    )
    assert projects.status_code == 403


@pytest.mark.asyncio
async def test_platform_admin_can_access_quality_api_for_benchmark_workspace(
    client: AsyncClient,
) -> None:
    async with async_session_factory() as db:
        await BenchmarkWorkspaceService(db).ensure_workspace()
        await db.commit()

    admin = await _register(client, f"platform-{uuid4().hex[:6]}@example.com")
    await _make_platform_admin(admin["user"]["id"])
    headers = _headers(admin["tokens"])

    summary = await client.get("/api/v1/platform/quality/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["success"] is True

    runs = await client.get("/api/v1/platform/quality/runs", headers=headers)
    assert runs.status_code == 200


@pytest.mark.asyncio
async def test_platform_admin_cannot_access_system_scope_via_org_api(client: AsyncClient) -> None:
    async with async_session_factory() as db:
        await BenchmarkWorkspaceService(db).ensure_workspace()
        system_org_id = (
            await db.execute(select(Organization).where(Organization.slug == BENCHMARK_ORG_SLUG))
        ).scalar_one().id
        await db.commit()

    admin = await _register(client, f"platform-org-{uuid4().hex[:6]}@example.com")
    await _make_platform_admin(admin["user"]["id"])
    headers = _headers(admin["tokens"])

    detail = await client.get(f"/api/v1/organizations/{system_org_id}", headers=headers)
    assert detail.status_code == 404


@pytest.mark.asyncio
async def test_support_grant_read_only_access(client: AsyncClient) -> None:
    customer = await _register(client, f"grant-ro-{uuid4().hex[:6]}@example.com")
    admin = await _register(client, f"grant-admin-{uuid4().hex[:6]}@example.com")
    await _make_platform_admin(admin["user"]["id"])

    customer_headers = _headers(customer["tokens"])
    admin_headers = _headers(admin["tokens"])
    org = await _create_org(client, customer_headers, "Grant Read Org")

    denied = await client.get(
        f"/api/v1/organizations/{org['id']}/projects",
        headers=admin_headers,
    )
    assert denied.status_code == 403

    grant_resp = await client.post(
        "/api/v1/platform/support-grants",
        json={
            "organization_id": org["id"],
            "granted_to_user_id": admin["user"]["id"],
            "reason": "Read-only investigation for ticket #999",
            "duration_hours": 12,
        },
        headers=admin_headers,
    )
    assert grant_resp.status_code == 201

    allowed = await client.get(
        f"/api/v1/organizations/{org['id']}/projects",
        headers=admin_headers,
    )
    assert allowed.status_code == 200


@pytest.mark.asyncio
async def test_expired_support_grant_is_rejected(client: AsyncClient) -> None:
    customer = await _register(client, f"grant-exp-{uuid4().hex[:6]}@example.com")
    admin = await _register(client, f"grant-exp-admin-{uuid4().hex[:6]}@example.com")
    await _make_platform_admin(admin["user"]["id"])

    customer_headers = _headers(customer["tokens"])
    admin_headers = _headers(admin["tokens"])
    org = await _create_org(client, customer_headers, "Expired Grant Org")

    grant = (
        await client.post(
            "/api/v1/platform/support-grants",
            json={
                "organization_id": org["id"],
                "granted_to_user_id": admin["user"]["id"],
                "reason": "Temporary access that should expire",
                "duration_hours": 24,
            },
            headers=admin_headers,
        )
    ).json()["data"]

    async with async_session_factory() as session:
        await session.execute(
            update(OrganizationSupportGrant)
            .where(OrganizationSupportGrant.id == UUID(grant["id"]))
            .values(expires_at=datetime.now(UTC) - timedelta(hours=1))
        )
        await session.commit()

    blocked = await client.get(
        f"/api/v1/organizations/{org['id']}/projects",
        headers=admin_headers,
    )
    assert blocked.status_code == 403


@pytest.mark.asyncio
async def test_revoked_support_grant_is_rejected(client: AsyncClient) -> None:
    customer = await _register(client, f"grant-rev-{uuid4().hex[:6]}@example.com")
    admin = await _register(client, f"grant-rev-admin-{uuid4().hex[:6]}@example.com")
    await _make_platform_admin(admin["user"]["id"])

    customer_headers = _headers(customer["tokens"])
    admin_headers = _headers(admin["tokens"])
    org = await _create_org(client, customer_headers, "Revoked Grant Org")

    grant = (
        await client.post(
            "/api/v1/platform/support-grants",
            json={
                "organization_id": org["id"],
                "granted_to_user_id": admin["user"]["id"],
                "reason": "Access to be revoked during test",
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


@pytest.mark.asyncio
async def test_support_grant_cannot_target_system_scope_organization(client: AsyncClient) -> None:
    async with async_session_factory() as db:
        await BenchmarkWorkspaceService(db).ensure_workspace()
        system_org_id = (
            await db.execute(select(Organization).where(Organization.slug == BENCHMARK_ORG_SLUG))
        ).scalar_one().id
        await db.commit()

    admin = await _register(client, f"grant-sys-{uuid4().hex[:6]}@example.com")
    await _make_platform_admin(admin["user"]["id"])
    headers = _headers(admin["tokens"])

    resp = await client.post(
        "/api/v1/platform/support-grants",
        json={
            "organization_id": str(system_org_id),
            "granted_to_user_id": admin["user"]["id"],
            "reason": "Should not be allowed for system scope",
            "duration_hours": 4,
        },
        headers=headers,
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_TARGET"


@pytest.mark.asyncio
async def test_viewer_cannot_create_project(client: AsyncClient) -> None:
    owner = await _register(client, f"owner-viewer-{uuid4().hex[:6]}@example.com")
    viewer = await _register(client, f"viewer-{uuid4().hex[:6]}@example.com")

    owner_headers = _headers(owner["tokens"])
    org = await _create_org(client, owner_headers, "Viewer Test Org")

    invite = await client.post(
        f"/api/v1/organizations/{org['id']}/members/invite",
        json={"email": viewer["user"]["email"], "role": "viewer"},
        headers=owner_headers,
    )
    assert invite.status_code == 201

    viewer_headers = _headers(viewer["tokens"])
    create = await client.post(
        f"/api/v1/organizations/{org['id']}/projects",
        json={"name": "Blocked Project", "environment": "staging"},
        headers=viewer_headers,
    )
    assert create.status_code == 403


@pytest.mark.asyncio
async def test_owner_can_update_organization(client: AsyncClient) -> None:
    owner = await _register(client, f"owner-update-{uuid4().hex[:6]}@example.com")
    headers = _headers(owner["tokens"])
    org = await _create_org(client, headers, "Owner Update Org")

    update_resp = await client.patch(
        f"/api/v1/organizations/{org['id']}",
        json={"name": "Renamed Organization"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["name"] == "Renamed Organization"


@pytest.mark.asyncio
async def test_admin_can_create_project(client: AsyncClient) -> None:
    owner = await _register(client, f"owner-admin-{uuid4().hex[:6]}@example.com")
    admin_user = await _register(client, f"admin-member-{uuid4().hex[:6]}@example.com")

    owner_headers = _headers(owner["tokens"])
    org = await _create_org(client, owner_headers, "Admin Test Org")

    invite = await client.post(
        f"/api/v1/organizations/{org['id']}/members/invite",
        json={"email": admin_user["user"]["email"], "role": "admin"},
        headers=owner_headers,
    )
    assert invite.status_code == 201

    admin_headers = _headers(admin_user["tokens"])
    create = await client.post(
        f"/api/v1/organizations/{org['id']}/projects",
        json={"name": "Admin Project", "environment": "production"},
        headers=admin_headers,
    )
    assert create.status_code == 201


@pytest.mark.asyncio
async def test_benchmark_quality_api_requires_platform_admin(client: AsyncClient) -> None:
    user = await _register(client, f"non-admin-{uuid4().hex[:6]}@example.com")
    headers = _headers(user["tokens"])

    summary = await client.get("/api/v1/platform/quality/summary", headers=headers)
    assert summary.status_code == 403

    runs = await client.get("/api/v1/platform/quality/runs", headers=headers)
    assert runs.status_code == 403
