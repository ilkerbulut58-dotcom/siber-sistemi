"""Closed pilot simulation — onboarding, limits, kill switch, emergency stop."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.models.scan import ScanJob, ScanStatus
from tests.pilot.fixtures import PilotWorld, audit_entries, scan_payload


@pytest.mark.asyncio
async def test_01_successful_pilot_onboarding(
    client: AsyncClient,
    pilot_world: PilotWorld,
    db_session,
) -> None:
    tenant = pilot_world.tenants["A"]
    with patch("app.api.v1.scans.dispatch_scan_job", new_callable=AsyncMock):
        resp = await client.post(
            f"/api/v1/organizations/{tenant.org_id}/scans",
            json=scan_payload(tenant, "deep"),
            headers=tenant.owner.headers,
        )
    assert resp.status_code == 201
    scan_id = resp.json()["data"]["id"]

    scan = (
        await db_session.execute(select(ScanJob).where(ScanJob.id == UUID(scan_id)))
    ).scalar_one()
    scan.status = ScanStatus.COMPLETED
    scan.completed_at = datetime.now(UTC)
    await db_session.commit()

    report = await client.get(
        f"/api/v1/organizations/{tenant.org_id}/scans/{scan_id}/report?format=json",
        headers=tenant.owner.headers,
    )
    assert report.status_code == 200

    audits = await audit_entries(db_session, tenant.org_id, action="scan.started")
    assert len(audits) >= 1


@pytest.mark.asyncio
async def test_02_unverified_domain_rejects_active_scan(
    client: AsyncClient,
    pilot_world: PilotWorld,
    db_session,
) -> None:
    tenant = pilot_world.tenants["B"]
    before = await db_session.scalar(select(func.count()).select_from(ScanJob))

    with patch("app.scanners.orchestrator.run_scan_for_profile", new_callable=AsyncMock) as mock_scan:
        resp = await client.post(
            f"/api/v1/organizations/{tenant.org_id}/scans",
            json=scan_payload(tenant, "deep"),
            headers=tenant.analyst.headers,
        )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "DOMAIN_NOT_VERIFIED"
    mock_scan.assert_not_called()

    after = await db_session.scalar(select(func.count()).select_from(ScanJob))
    assert after == before

    rejected = await audit_entries(db_session, tenant.org_id, action="scan.rejected")
    assert any(e.details.get("reason_code") == "DOMAIN_NOT_VERIFIED" for e in rejected)


@pytest.mark.asyncio
async def test_03_platform_admin_manual_domain_approval(
    client: AsyncClient,
    pilot_world: PilotWorld,
    db_session,
) -> None:
    tenant = pilot_world.tenants["B"]
    admin = pilot_world.platform_admin
    assert admin is not None

    verify = await client.post(
        f"/api/v1/platform/pilot-tenants/{tenant.org_id}/projects/{tenant.project_id}/domains/{tenant.domain_id}/verify",
        headers=admin.headers,
    )
    assert verify.status_code == 200
    body = verify.json()["data"]
    assert body["is_verified"] is True
    assert body["active_scan_allowed"] is True

    with patch("app.api.v1.scans.dispatch_scan_job", new_callable=AsyncMock):
        scan = await client.post(
            f"/api/v1/organizations/{tenant.org_id}/scans",
            json=scan_payload(tenant, "deep"),
            headers=tenant.analyst.headers,
        )
    assert scan.status_code == 201

    audits = await audit_entries(db_session, tenant.org_id, action="domain.verified")
    assert len(audits) >= 1


@pytest.mark.asyncio
async def test_04_quota_exceeded(
    client: AsyncClient,
    pilot_world: PilotWorld,
    db_session,
) -> None:
    tenant = pilot_world.tenants["C"]
    before = await db_session.scalar(
        select(func.count()).select_from(ScanJob).where(ScanJob.organization_id == UUID(tenant.org_id))
    )

    resp = await client.post(
        f"/api/v1/organizations/{tenant.org_id}/scans",
        json=scan_payload(tenant, "safe"),
        headers=tenant.analyst.headers,
    )
    assert resp.status_code == 429
    assert resp.json()["error"]["code"] == "SCAN_QUOTA_EXCEEDED"

    after = await db_session.scalar(
        select(func.count()).select_from(ScanJob).where(ScanJob.organization_id == UUID(tenant.org_id))
    )
    assert after == before


@pytest.mark.asyncio
async def test_05_pilot_expired(
    client: AsyncClient,
    pilot_world: PilotWorld,
    db_session,
) -> None:
    tenant = pilot_world.tenants["D"]
    resp = await client.post(
        f"/api/v1/organizations/{tenant.org_id}/scans",
        json=scan_payload(tenant, "safe"),
        headers=tenant.owner.headers,
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "PILOT_EXPIRED"


@pytest.mark.asyncio
async def test_06_kill_switch_and_recovery(
    client: AsyncClient,
    pilot_world: PilotWorld,
    db_session,
) -> None:
    tenant = pilot_world.tenants["E"]
    admin = pilot_world.platform_admin
    assert admin is not None

    blocked = await client.post(
        f"/api/v1/organizations/{tenant.org_id}/scans",
        json=scan_payload(tenant, "safe"),
        headers=tenant.owner.headers,
    )
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "PILOT_SCANS_DISABLED"

    toggle = await client.patch(
        f"/api/v1/platform/pilot-tenants/{tenant.org_id}",
        json={"scans_disabled": False},
        headers=admin.headers,
    )
    assert toggle.status_code == 200

    with patch("app.api.v1.scans.dispatch_scan_job", new_callable=AsyncMock):
        allowed = await client.post(
            f"/api/v1/organizations/{tenant.org_id}/scans",
            json=scan_payload(tenant, "safe"),
            headers=tenant.owner.headers,
        )
    assert allowed.status_code == 201


@pytest.mark.asyncio
async def test_14_emergency_scan_cancellation(
    client: AsyncClient,
    pilot_world: PilotWorld,
    db_session,
) -> None:
    tenant = pilot_world.tenants["A"]
    with patch("app.api.v1.scans.dispatch_scan_job", new_callable=AsyncMock):
        created = await client.post(
            f"/api/v1/organizations/{tenant.org_id}/scans",
            json=scan_payload(tenant, "safe"),
            headers=tenant.analyst.headers,
        )
    assert created.status_code == 201
    scan_id = created.json()["data"]["id"]

    cancelled = await client.post(
        f"/api/v1/organizations/{tenant.org_id}/scans/{scan_id}/cancel",
        headers=tenant.analyst.headers,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["data"]["status"] == "cancelled"

    audits = await audit_entries(db_session, tenant.org_id, action="scan.cancelled")
    assert any(str(a.resource_id) == scan_id for a in audits)
