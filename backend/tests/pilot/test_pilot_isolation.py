"""Tenant isolation for closed pilot simulation."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.pilot.fixtures import PilotWorld, scan_payload


@pytest.mark.asyncio
async def test_07_tenant_isolation(client: AsyncClient, pilot_world: PilotWorld) -> None:
    tenant_a = pilot_world.tenants["A"]
    tenant_b = pilot_world.tenants["B"]
    headers_a = tenant_a.owner.headers

    assert (await client.get(f"/api/v1/organizations/{tenant_b.org_id}", headers=headers_a)).status_code in (
        403,
        404,
    )
    assert (
        await client.get(
            f"/api/v1/organizations/{tenant_b.org_id}/projects",
            headers=headers_a,
        )
    ).status_code == 403
    assert (
        await client.get(
            f"/api/v1/organizations/{tenant_b.org_id}/projects/{tenant_b.project_id}/domains",
            headers=headers_a,
        )
    ).status_code == 403
    assert (
        await client.get(f"/api/v1/organizations/{tenant_b.org_id}/scans", headers=headers_a)
    ).status_code == 403
    assert (
        await client.get(f"/api/v1/organizations/{tenant_b.org_id}/findings", headers=headers_a)
    ).status_code == 403
    assert (
        await client.patch(
            f"/api/v1/organizations/{tenant_b.org_id}/findings/{uuid4()}",
            json={"status": "false_positive"},
            headers=headers_a,
        )
    ).status_code in (403, 404)
    assert (
        await client.post(
            f"/api/v1/organizations/{tenant_b.org_id}/scans",
            json=scan_payload(tenant_b, "safe"),
            headers=headers_a,
        )
    ).status_code == 403
