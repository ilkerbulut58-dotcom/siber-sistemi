"""Scan profile permissions in closed pilot simulation."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.scan import ScanJob, ScanStatus
from tests.pilot.fixtures import PilotWorld, scan_payload


async def _release_concurrency_slot(db_session, scan_id: str) -> None:
    scan = (
        await db_session.execute(select(ScanJob).where(ScanJob.id == UUID(scan_id)))
    ).scalar_one()
    scan.status = ScanStatus.COMPLETED
    scan.completed_at = datetime.now(UTC)
    await db_session.commit()


@pytest.mark.asyncio
async def test_09_scan_profile_permissions(
    client: AsyncClient,
    pilot_world: PilotWorld,
    db_session,
) -> None:
    tenant = pilot_world.tenants["A"]

    with patch("app.api.v1.scans.dispatch_scan_job", new_callable=AsyncMock):
        passive = await client.post(
            f"/api/v1/organizations/{tenant.org_id}/scans",
            json=scan_payload(tenant, "safe"),
            headers=tenant.analyst.headers,
        )
    assert passive.status_code == 201
    await _release_concurrency_slot(db_session, passive.json()["data"]["id"])

    with patch("app.api.v1.scans.dispatch_scan_job", new_callable=AsyncMock):
        safe_active = await client.post(
            f"/api/v1/organizations/{tenant.org_id}/scans",
            json=scan_payload(tenant, "deep"),
            headers=tenant.analyst.headers,
        )
    assert safe_active.status_code == 201
    await _release_concurrency_slot(db_session, safe_active.json()["data"]["id"])

    with patch("app.api.v1.scans.dispatch_scan_job", new_callable=AsyncMock):
        full_active = await client.post(
            f"/api/v1/organizations/{tenant.org_id}/scans",
            json=scan_payload(tenant, "code"),
            headers=tenant.analyst.headers,
        )
    assert full_active.status_code == 201
