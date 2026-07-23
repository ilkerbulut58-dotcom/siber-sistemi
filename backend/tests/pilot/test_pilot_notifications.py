"""Notification abstraction tests for closed pilot simulation."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.notifications.service import (
    notify_critical_finding,
    notify_pilot_expired,
    notify_quota_exceeded,
    notify_scan_completed,
    notify_scan_failed,
    notify_verification_required,
)
from tests.pilot.capture_provider import CaptureNotificationProvider
from tests.pilot.fixtures import PilotWorld, scan_payload


@pytest.mark.asyncio
async def test_12_notification_abstraction_no_secrets(
    capture_notifications: CaptureNotificationProvider,
) -> None:
    org_id = uuid4()
    user_id = uuid4()
    await notify_scan_completed(
        user_id=user_id,
        organization_id=org_id,
        scan_id=uuid4(),
        target="http://pilot-a.pilot-sim.example.com/",
        findings_count=1,
    )
    await notify_scan_failed(
        user_id=user_id,
        organization_id=org_id,
        scan_id=uuid4(),
        target="http://pilot-a.pilot-sim.example.com/",
        error="simulated",
    )
    await notify_quota_exceeded(user_id=user_id, organization_id=org_id, quota=2)
    await notify_verification_required(
        user_id=user_id,
        organization_id=org_id,
        domain_hostname="pilot-b.pilot-sim.example.com",
    )
    await notify_pilot_expired(user_id=user_id, organization_id=org_id)
    await notify_critical_finding(
        user_id=user_id,
        organization_id=org_id,
        finding_id=uuid4(),
        title="Critical simulation",
    )

    assert len(capture_notifications.events) == 6
    for event in capture_notifications.events:
        payload = str(event)
        assert "PilotSim123!" not in payload
        assert "SECRET" not in payload.upper()
        assert "password" not in payload.lower()


@pytest.mark.asyncio
async def test_12_quota_notification_on_scan_rejection(
    client: AsyncClient,
    pilot_world: PilotWorld,
    capture_notifications: CaptureNotificationProvider,
) -> None:
    tenant = pilot_world.tenants["C"]
    capture_notifications.clear()
    await client.post(
        f"/api/v1/organizations/{tenant.org_id}/scans",
        json=scan_payload(tenant, "safe"),
        headers=tenant.analyst.headers,
    )
    types = {e["event_type"] for e in capture_notifications.events}
    assert "quota.exceeded" in types
