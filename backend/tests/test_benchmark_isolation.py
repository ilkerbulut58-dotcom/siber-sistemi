"""Tests for system-scope benchmark isolation."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.organization import Organization
from app.services.benchmark_workspace_service import BENCHMARK_ORG_SLUG, BenchmarkWorkspaceService


@pytest.mark.asyncio
async def test_system_scope_org_hidden_from_customer_lists(client: AsyncClient) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": f"user-{uuid4().hex[:6]}@example.com", "password": "SecurePass123!", "full_name": "User"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['data']['tokens']['access_token']}"}
    orgs = (await client.get("/api/v1/organizations", headers=headers)).json()["data"]
    assert all(org["slug"] != BENCHMARK_ORG_SLUG for org in orgs)


@pytest.mark.asyncio
async def test_system_scope_org_not_accessible_via_org_api(client: AsyncClient) -> None:
    from app.core.database import async_session_factory

    async with async_session_factory() as db:
        await BenchmarkWorkspaceService(db).ensure_workspace()
        org_id = (
            await db.execute(select(Organization).where(Organization.slug == BENCHMARK_ORG_SLUG))
        ).scalar_one().id
        await db.commit()

    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": f"user-{uuid4().hex[:6]}@example.com", "password": "SecurePass123!", "full_name": "User"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['data']['tokens']['access_token']}"}
    response = await client.get(f"/api/v1/organizations/{org_id}", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_platform_quality_requires_admin(client: AsyncClient) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": f"user-{uuid4().hex[:6]}@example.com", "password": "SecurePass123!", "full_name": "User"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['data']['tokens']['access_token']}"}
    response = await client.get("/api/v1/platform/quality/summary", headers=headers)
    assert response.status_code == 403
