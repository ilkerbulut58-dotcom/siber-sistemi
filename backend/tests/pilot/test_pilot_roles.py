"""Role enforcement for closed pilot simulation."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.pilot.fixtures import PilotWorld, scan_payload


@pytest.mark.asyncio
async def test_08_role_permissions(client: AsyncClient, pilot_world: PilotWorld) -> None:
    tenant = pilot_world.tenants["A"]
    admin = pilot_world.platform_admin
    assert admin is not None

    viewer_scan = await client.post(
        f"/api/v1/organizations/{tenant.org_id}/scans",
        json=scan_payload(tenant, "safe"),
        headers=tenant.viewer.headers,
    )
    assert viewer_scan.status_code == 403

    owner_platform = await client.get(
        "/api/v1/platform/pilot-tenants",
        headers=tenant.owner.headers,
    )
    assert owner_platform.status_code == 403

    analyst_settings = await client.patch(
        f"/api/v1/organizations/{tenant.org_id}",
        json={"name": "Renamed By Analyst"},
        headers=tenant.analyst.headers,
    )
    assert analyst_settings.status_code == 403

    admin_list = await client.get("/api/v1/platform/pilot-tenants", headers=admin.headers)
    assert admin_list.status_code == 200
