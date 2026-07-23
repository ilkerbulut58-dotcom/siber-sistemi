"""Pilot tenant gate tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update

from app.core.database import async_session_factory
from app.core.exceptions import AppError
from app.models.organization import Organization
from app.models.user import User
from app.services.pilot_service import PilotService


async def _register(client: AsyncClient, email: str) -> tuple[dict, dict]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePass123!", "full_name": "Pilot User"},
    )
    assert reg.status_code == 201
    data = reg.json()["data"]
    headers = {"Authorization": f"Bearer {data['tokens']['access_token']}"}
    org = (
        await client.post("/api/v1/organizations", json={"name": "Pilot Org"}, headers=headers)
    ).json()["data"]
    return headers, org


async def _make_platform_admin(user_id: str) -> None:
    async with async_session_factory() as session:
        await session.execute(
            update(User).where(User.id == UUID(user_id)).values(is_platform_admin=True)
        )
        await session.commit()


def test_pilot_assert_can_scan_expired() -> None:
    org = Organization(
        id=uuid4(),
        name="Expired",
        slug="expired",
        owner_id=uuid4(),
        is_active=True,
        is_pilot=True,
        pilot_ends_at=datetime.now(UTC) - timedelta(hours=1),
    )
    with pytest.raises(AppError) as exc:
        PilotService.assert_can_scan(org)
    assert exc.value.code == "PILOT_EXPIRED"


def test_pilot_assert_scans_disabled() -> None:
    org = Organization(
        id=uuid4(),
        name="Disabled",
        slug="disabled",
        owner_id=uuid4(),
        is_active=True,
        is_pilot=True,
        scans_disabled=True,
    )
    with pytest.raises(AppError) as exc:
        PilotService.assert_can_scan(org)
    assert exc.value.code == "PILOT_SCANS_DISABLED"


def test_pilot_effective_quota() -> None:
    org = Organization(
        id=uuid4(),
        name="Quota",
        slug="quota",
        owner_id=uuid4(),
        is_pilot=True,
        pilot_scan_quota=3,
    )
    assert PilotService.effective_daily_quota(org, 50) == 3


@pytest.mark.asyncio
async def test_platform_admin_updates_pilot_tenant(client: AsyncClient) -> None:
    admin_headers, _admin_org = await _register(client, "admin-pilot@example.com")
    admin_user = (await client.get("/api/v1/users/me", headers=admin_headers)).json()["data"]
    await _make_platform_admin(admin_user["id"])

    _customer_headers, org = await _register(client, "customer-pilot@example.com")

    response = await client.patch(
        f"/api/v1/platform/pilot-tenants/{org['id']}",
        json={"is_pilot": True, "pilot_scan_quota": 5, "pilot_notes": "Wave 1"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["is_pilot"] is True
    assert body["pilot_scan_quota"] == 5

    listed = await client.get("/api/v1/platform/pilot-tenants", headers=admin_headers)
    assert listed.status_code == 200
    assert any(item["id"] == org["id"] for item in listed.json()["data"])


@pytest.mark.asyncio
async def test_onboarding_status_endpoint(client: AsyncClient) -> None:
    headers, org = await _register(client, "onboard@example.com")
    async with async_session_factory() as session:
        await session.execute(
            update(Organization)
            .where(Organization.id == UUID(org["id"]))
            .values(is_pilot=True)
        )
        await session.commit()

    response = await client.get(
        f"/api/v1/organizations/{org['id']}/onboarding-status",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["is_pilot"] is True
    assert body["ready_to_scan"] is False
    assert any(step["step_id"] == "email_verified" for step in body["steps"])
