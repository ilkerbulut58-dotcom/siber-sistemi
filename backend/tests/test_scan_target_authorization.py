"""Predefined test targets, DNS requirement, and admin assignments."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.models.scan_target import PredefinedScanTarget, ScanTargetAssignment
from app.models.user import User


async def _setup_org(client: AsyncClient, email: str = "dns-user@example.com") -> tuple[dict, dict, dict]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePass123!", "full_name": "User"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['data']['tokens']['access_token']}"}
    org = (await client.post("/api/v1/organizations", json={"name": "Org"}, headers=headers)).json()["data"]
    project = (
        await client.post(
            f"/api/v1/organizations/{org['id']}/projects",
            json={"name": "P", "environment": "staging"},
            headers=headers,
        )
    ).json()["data"]
    return headers, org, project


@pytest.mark.asyncio
@patch("app.services.domain_service.hostname_resolves", return_value=True)
async def test_unverified_domain_rejected(_mock: AsyncMock, client: AsyncClient) -> None:
    headers, org, project = await _setup_org(client, "unverified-scan@example.com")
    domain = (
        await client.post(
            f"/api/v1/organizations/{org['id']}/projects/{project['id']}/domains",
            json={"hostname": "needs-dns.example.com", "method": "dns_txt"},
            headers=headers,
        )
    ).json()["data"]
    assert domain["is_verified"] is False

    with patch("app.api.v1.scans.dispatch_scan_job", new_callable=AsyncMock):
        resp = await client.post(
            f"/api/v1/organizations/{org['id']}/scans",
            json={
                "project_id": project["id"],
                "domain_id": domain["id"],
                "scan_profile": "safe",
                "target_url": "https://needs-dns.example.com/",
                "authorization_accepted": True,
            },
            headers=headers,
        )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "DOMAIN_NOT_VERIFIED"


@pytest.mark.asyncio
@patch("app.services.domain_service.hostname_resolves", return_value=True)
async def test_assigned_predefined_target_without_dns(
    _mock: AsyncMock,
    client: AsyncClient,
    db_session,
) -> None:
    headers, org, project = await _setup_org(client, "assigned-test@example.com")
    me = (await client.get("/api/v1/users/me", headers=headers)).json()["data"]
    target = (
        await db_session.execute(
            select(PredefinedScanTarget).where(PredefinedScanTarget.hostname == "turbridge.de")
        )
    ).scalar_one_or_none()
    if target is None:
        target = PredefinedScanTarget(
            hostname="turbridge.de",
            display_name="turbridge.de",
            is_active=True,
            default_scan_profile="safe",
        )
        db_session.add(target)
        await db_session.flush()

    db_session.add(
        ScanTargetAssignment(
            predefined_target_id=target.id,
            user_id=UUID(me["id"]),
            organization_id=UUID(org["id"]),
            assigned_by_user_id=UUID(me["id"]),
            starts_at=datetime.now(UTC),
            allowed_profiles=["safe"],
        )
    )
    await db_session.commit()

    domain = (
        await client.post(
            f"/api/v1/organizations/{org['id']}/projects/{project['id']}/domains",
            json={"hostname": "turbridge.de", "method": "dns_txt"},
            headers=headers,
        )
    ).json()["data"]
    assert domain["is_verified"] is True

    with patch("app.api.v1.scans.dispatch_scan_job", new_callable=AsyncMock):
        resp = await client.post(
            f"/api/v1/organizations/{org['id']}/scans",
            json={
                "project_id": project["id"],
                "domain_id": domain["id"],
                "scan_profile": "safe",
                "target_url": "https://turbridge.de/",
                "authorization_accepted": True,
            },
            headers=headers,
        )
    assert resp.status_code == 201
    assert resp.json()["data"]["authorization_source"] == "admin_test_assignment"


@pytest.mark.asyncio
@patch("app.services.domain_service.hostname_resolves", return_value=True)
async def test_other_user_cannot_use_assigned_target(
    _mock: AsyncMock,
    client: AsyncClient,
    db_session,
) -> None:
    owner_headers, org, project = await _setup_org(client, "owner-assign@example.com")
    owner = (await client.get("/api/v1/users/me", headers=owner_headers)).json()["data"]

    reg2 = await client.post(
        "/api/v1/auth/register",
        json={"email": "other-assign@example.com", "password": "SecurePass123!", "full_name": "Other"},
    )
    other_headers = {"Authorization": f"Bearer {reg2.json()['data']['tokens']['access_token']}"}
    invite = await client.post(
        f"/api/v1/organizations/{org['id']}/members/invite",
        json={"email": "other-assign@example.com", "role": "security_analyst"},
        headers=owner_headers,
    )
    assert invite.status_code == 201

    target = PredefinedScanTarget(
        hostname="wolkeshopping.de",
        display_name="wolkeshopping.de",
        is_active=True,
        default_scan_profile="safe",
    )
    db_session.add(target)
    await db_session.flush()
    db_session.add(
        ScanTargetAssignment(
            predefined_target_id=target.id,
            user_id=UUID(owner["id"]),
            organization_id=UUID(org["id"]),
            assigned_by_user_id=UUID(owner["id"]),
            starts_at=datetime.now(UTC),
            allowed_profiles=["safe"],
        )
    )
    await db_session.commit()

    domain = (
        await client.post(
            f"/api/v1/organizations/{org['id']}/projects/{project['id']}/domains",
            json={"hostname": "wolkeshopping.de", "method": "dns_txt"},
            headers=other_headers,
        )
    ).json()["data"]
    assert domain["is_verified"] is False

    with patch("app.api.v1.scans.dispatch_scan_job", new_callable=AsyncMock):
        resp = await client.post(
            f"/api/v1/organizations/{org['id']}/scans",
            json={
                "project_id": project["id"],
                "domain_id": domain["id"],
                "scan_profile": "safe",
                "target_url": "https://wolkeshopping.de/",
                "authorization_accepted": True,
            },
            headers=other_headers,
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
@patch("app.services.domain_service.run_verification_detailed", new_callable=AsyncMock, return_value=(True, None))
@patch("app.services.domain_service.hostname_resolves", return_value=True)
async def test_admin_dns_exempt_user(
    _mock_dns: AsyncMock,
    _mock_verify: AsyncMock,
    client: AsyncClient,
) -> None:
    headers, org, project = await _setup_org(client, "admin-exempt@example.com")
    me = (await client.get("/api/v1/users/me", headers=headers)).json()["data"]
    async with async_session_factory() as session:
        await session.execute(
            update(User)
            .where(User.id == UUID(me["id"]))
            .values(dns_verification_exempt=True, is_email_verified=True)
        )
        await session.commit()

    with patch("app.services.domain_service.hostname_resolves", return_value=True):
        domain = (
            await client.post(
                f"/api/v1/organizations/{org['id']}/projects/{project['id']}/domains",
                json={"hostname": "exempt-target.example.com", "method": "dns_txt"},
                headers=headers,
            )
        ).json()["data"]

    verify = await client.post(
        f"/api/v1/organizations/{org['id']}/projects/{project['id']}/domains/{domain['id']}/verify",
        headers=headers,
    )
    assert verify.status_code == 200
    assert verify.json()["data"]["verified"] is True

    with patch("app.api.v1.scans.dispatch_scan_job", new_callable=AsyncMock):
        resp = await client.post(
            f"/api/v1/organizations/{org['id']}/scans",
            json={
                "project_id": project["id"],
                "domain_id": domain["id"],
                "scan_profile": "safe",
                "target_url": "https://exempt-target.example.com/",
                "authorization_accepted": True,
            },
            headers=headers,
        )
    assert resp.status_code == 201
    assert resp.json()["data"]["authorization_source"] == "admin_dns_exempt"


@pytest.mark.asyncio
@patch("app.services.domain_service.hostname_resolves", return_value=True)
async def test_revoked_assignment_blocks_worker(
    _mock: AsyncMock,
    client: AsyncClient,
    db_session,
) -> None:
    from datetime import UTC, datetime

    from app.core.database import async_session_factory
    from app.models.scan import ScanJob, ScanStatus
    from app.services.scan_service import run_scan_job

    headers, org, project = await _setup_org(client, "revoke-worker@example.com")
    me = (await client.get("/api/v1/users/me", headers=headers)).json()["data"]
    target = PredefinedScanTarget(
        hostname="revoke-worker.example.com",
        display_name="revoke-worker.example.com",
        is_active=True,
        default_scan_profile="safe",
    )
    db_session.add(target)
    await db_session.flush()
    assignment = ScanTargetAssignment(
        predefined_target_id=target.id,
        user_id=UUID(me["id"]),
        organization_id=UUID(org["id"]),
        assigned_by_user_id=UUID(me["id"]),
        starts_at=datetime.now(UTC),
        allowed_profiles=["safe"],
    )
    db_session.add(assignment)
    await db_session.commit()

    domain = (
        await client.post(
            f"/api/v1/organizations/{org['id']}/projects/{project['id']}/domains",
            json={"hostname": "revoke-worker.example.com", "method": "dns_txt"},
            headers=headers,
        )
    ).json()["data"]

    with patch("app.api.v1.scans.dispatch_scan_job", new_callable=AsyncMock):
        scan_resp = await client.post(
            f"/api/v1/organizations/{org['id']}/scans",
            json={
                "project_id": project["id"],
                "domain_id": domain["id"],
                "scan_profile": "safe",
                "target_url": "https://revoke-worker.example.com/",
                "authorization_accepted": True,
            },
            headers=headers,
        )
    assert scan_resp.status_code == 201
    scan_id = scan_resp.json()["data"]["id"]

    assignment.revoked_at = datetime.now(UTC)
    await db_session.commit()

    with patch("app.services.scan_service.run_scan_for_profile", new_callable=AsyncMock, return_value=[]):
        await run_scan_job(UUID(scan_id), async_session_factory)

    row = (
        await db_session.execute(select(ScanJob).where(ScanJob.id == UUID(scan_id)))
    ).scalar_one()
    assert row.status == ScanStatus.FAILED.value
