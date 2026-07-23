"""Finding feedback lifecycle in closed pilot simulation."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import Finding, FindingSeverity, FindingStatus
from tests.pilot.fixtures import PilotWorld, SimTenant, audit_entries


async def _seed_finding(db: AsyncSession, tenant: SimTenant) -> Finding:
    finding = Finding(
        id=uuid4(),
        organization_id=UUID(tenant.org_id),
        project_id=UUID(tenant.project_id),
        source_tool="pilot-sim",
        title="Simulation finding",
        severity=FindingSeverity.MEDIUM,
        fingerprint=f"pilot-sim-{tenant.key}-{uuid4().hex[:8]}",
        status=FindingStatus.OPEN,
    )
    db.add(finding)
    await db.commit()
    return finding


@pytest.mark.asyncio
async def test_11_finding_feedback_audit(
    client: AsyncClient,
    pilot_world: PilotWorld,
    db_session: AsyncSession,
) -> None:
    tenant = pilot_world.tenants["A"]
    other = pilot_world.tenants["B"]
    finding = await _seed_finding(db_session, tenant)

    statuses = [
        "false_positive",
        "resolved",
        "accepted_risk",
        "needs_help",
        "duplicate",
        "not_applicable",
    ]
    for status in statuses:
        resp = await client.patch(
            f"/api/v1/organizations/{tenant.org_id}/findings/{finding.id}",
            json={"status": status, "reviewer_notes": f"pilot sim {status}"},
            headers=tenant.analyst.headers,
        )
        assert resp.status_code == 200

    audits = await audit_entries(db_session, tenant.org_id, action="finding.feedback_submitted")
    assert len(audits) >= len(statuses)

    cross = await client.patch(
        f"/api/v1/organizations/{other.org_id}/findings/{finding.id}",
        json={"status": "false_positive"},
        headers=tenant.analyst.headers,
    )
    assert cross.status_code in (403, 404)
