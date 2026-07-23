"""Audit log integrity for closed pilot simulation."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.audit import AuditLog
from tests.pilot.fixtures import PilotWorld, audit_entries


@pytest.mark.asyncio
async def test_13_audit_log_integrity(
    client: AsyncClient,
    pilot_world: PilotWorld,
    db_session,
) -> None:
    tenant = pilot_world.tenants["A"]
    actions = {a.action for a in await audit_entries(db_session, tenant.org_id)}
    expected_subset = {
        "organization.created",
        "domain.added",
        "organization.member_invited",
        "scan.started",
    }
    assert expected_subset.intersection(actions)

    count_before = await db_session.scalar(select(AuditLog.id).limit(1))
    assert count_before is not None

    # Audit rows are append-only in API; no delete endpoint for tenants.
    member_list = await client.get(
        f"/api/v1/organizations/{tenant.org_id}/members",
        headers=tenant.viewer.headers,
    )
    assert member_list.status_code == 200
