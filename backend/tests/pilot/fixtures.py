"""Deterministic closed-pilot simulation fixtures (lab hostnames only)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.audit import AuditLog
from app.models.mixins import OrganizationRole
from app.models.organization import Organization
from app.models.scan import ScanJob, ScanStatus
from app.models.user import User

PILOT_SIM_PASSWORD = "PilotSim123!"
SIM_DOMAIN = "pilot-sim.example.com"
PILOT_START = datetime(2026, 1, 1, tzinfo=UTC)
PILOT_END_FUTURE = datetime(2027, 6, 1, tzinfo=UTC)
PILOT_END_PAST = datetime(2025, 6, 1, tzinfo=UTC)


@dataclass
class SimUser:
    email: str
    user_id: str
    headers: dict[str, str]
    role: str


@dataclass
class SimTenant:
    key: str
    slug: str
    org_id: str
    project_id: str
    domain_id: str
    hostname: str
    target_url: str
    owner: SimUser
    analyst: SimUser
    viewer: SimUser
    domain_verified: bool = True
    pilot_scan_quota: int | None = 10
    scans_disabled: bool = False
    pilot_ends_at: datetime | None = None


@dataclass
class PilotWorld:
    tenants: dict[str, SimTenant] = field(default_factory=dict)
    platform_admin: SimUser | None = None


def lab_hostname(tenant_key: str) -> str:
    return f"pilot-{tenant_key.lower()}.{SIM_DOMAIN}"


def sim_email(local: str) -> str:
    return f"{local}@{SIM_DOMAIN}"


def lab_target(tenant_key: str) -> str:
    return f"http://{lab_hostname(tenant_key)}/"


async def _register(client: AsyncClient, email: str, full_name: str) -> SimUser:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PILOT_SIM_PASSWORD, "full_name": full_name},
    )
    assert reg.status_code == 201, reg.text
    data = reg.json()["data"]
    token = data["tokens"]["access_token"]
    return SimUser(
        email=email,
        user_id=data["user"]["id"],
        headers={"Authorization": f"Bearer {token}"},
        role="",
    )


async def _make_platform_admin(user_id: str, db: AsyncSession) -> None:
    await db.execute(
        update(User).where(User.id == UUID(user_id)).values(is_platform_admin=True)
    )
    await db.commit()


async def _invite_member(
    client: AsyncClient,
    owner_headers: dict[str, str],
    org_id: str,
    email: str,
    role: OrganizationRole,
) -> SimUser:
    await _register(client, email, email.split("@")[0])
    resp = await client.post(
        f"/api/v1/organizations/{org_id}/members/invite",
        json={"email": email, "role": role.value},
        headers=owner_headers,
    )
    assert resp.status_code == 201, resp.text
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PILOT_SIM_PASSWORD},
    )
    assert login.status_code == 200, login.text
    token = login.json()["data"]["tokens"]["access_token"]
    return SimUser(
        email=email,
        user_id=login.json()["data"]["user"]["id"],
        headers={"Authorization": f"Bearer {token}"},
        role=role.value,
    )


async def _seed_tenant(
    client: AsyncClient,
    db: AsyncSession,
    *,
    key: str,
    domain_verified: bool,
    pilot_scan_quota: int | None,
    scans_disabled: bool,
    pilot_ends_at: datetime | None,
    prefill_scans: int = 0,
) -> SimTenant:
    hostname = lab_hostname(key)
    owner_email = sim_email(f"owner-{key}")
    analyst_email = sim_email(f"analyst-{key}")
    viewer_email = sim_email(f"viewer-{key}")

    owner = await _register(client, owner_email, f"Owner {key}")
    org = (
        await client.post(
            "/api/v1/organizations",
            json={"name": f"Pilot Tenant {key.upper()}"},
            headers=owner.headers,
        )
    ).json()["data"]

    await db.execute(
        update(Organization)
        .where(Organization.id == UUID(org["id"]))
        .values(
            is_pilot=True,
            pilot_starts_at=PILOT_START,
            pilot_ends_at=pilot_ends_at or PILOT_END_FUTURE,
            pilot_scan_quota=pilot_scan_quota,
            pilot_active_scan_allowed=True,
            scans_disabled=scans_disabled,
        )
    )
    await db.commit()

    project = (
        await client.post(
            f"/api/v1/organizations/{org['id']}/projects",
            json={"name": f"Lab Project {key}", "environment": "staging"},
            headers=owner.headers,
        )
    ).json()["data"]

    from unittest.mock import patch

    with patch("app.services.domain_service.hostname_resolves", return_value=True):
        domain = (
            await client.post(
                f"/api/v1/organizations/{org['id']}/projects/{project['id']}/domains",
                json={"hostname": hostname, "method": "dns_txt"},
                headers=owner.headers,
            )
        ).json()["data"]

    if domain_verified:
        from app.models.domain import Domain

        row = (await db.execute(select(Domain).where(Domain.id == UUID(domain["id"])))).scalar_one()
        row.is_verified = True
        row.verified_at = datetime.now(UTC)
        row.verification_method = "dns_txt"
        row.active_scan_allowed = True
        await db.commit()
    else:
        from app.models.domain import Domain

        row = (await db.execute(select(Domain).where(Domain.id == UUID(domain["id"])))).scalar_one()
        row.is_verified = False
        row.active_scan_allowed = False
        await db.commit()

    analyst = await _invite_member(
        client, owner.headers, org["id"], analyst_email, OrganizationRole.SECURITY_ANALYST
    )
    viewer = await _invite_member(
        client, owner.headers, org["id"], viewer_email, OrganizationRole.VIEWER
    )
    owner.role = OrganizationRole.OWNER.value
    analyst.role = OrganizationRole.SECURITY_ANALYST.value
    viewer.role = OrganizationRole.VIEWER.value

    if prefill_scans > 0:
        for _ in range(prefill_scans):
            db.add(
                ScanJob(
                    organization_id=UUID(org["id"]),
                    project_id=UUID(project["id"]),
                    domain_id=UUID(domain["id"]),
                    initiated_by=UUID(owner.user_id),
                    scan_profile="safe",
                    target_url=lab_target(key),
                    status=ScanStatus.COMPLETED,
                    completed_at=datetime.now(UTC),
                )
            )
        await db.commit()

    return SimTenant(
        key=key,
        slug=f"pilot-{key}",
        org_id=org["id"],
        project_id=project["id"],
        domain_id=domain["id"],
        hostname=hostname,
        target_url=lab_target(key),
        owner=owner,
        analyst=analyst,
        viewer=viewer,
        domain_verified=domain_verified,
        pilot_scan_quota=pilot_scan_quota,
        scans_disabled=scans_disabled,
        pilot_ends_at=pilot_ends_at,
    )


async def build_pilot_world(client: AsyncClient, db: AsyncSession) -> PilotWorld:
    get_settings.cache_clear()
    world = PilotWorld()
    world.tenants["A"] = await _seed_tenant(
        client,
        db,
        key="a",
        domain_verified=True,
        pilot_scan_quota=10,
        scans_disabled=False,
        pilot_ends_at=None,
    )
    world.tenants["B"] = await _seed_tenant(
        client,
        db,
        key="b",
        domain_verified=False,
        pilot_scan_quota=10,
        scans_disabled=False,
        pilot_ends_at=None,
    )
    world.tenants["C"] = await _seed_tenant(
        client,
        db,
        key="c",
        domain_verified=True,
        pilot_scan_quota=2,
        scans_disabled=False,
        pilot_ends_at=None,
        prefill_scans=2,
    )
    world.tenants["D"] = await _seed_tenant(
        client,
        db,
        key="d",
        domain_verified=True,
        pilot_scan_quota=10,
        scans_disabled=False,
        pilot_ends_at=PILOT_END_PAST,
    )
    world.tenants["E"] = await _seed_tenant(
        client,
        db,
        key="e",
        domain_verified=True,
        pilot_scan_quota=10,
        scans_disabled=True,
        pilot_ends_at=None,
    )

    admin = await _register(client, sim_email("platform-admin"), "Platform Admin")
    await _make_platform_admin(admin.user_id, db)
    admin.role = "platform_admin"
    world.platform_admin = admin
    return world


async def audit_entries(
    db: AsyncSession,
    organization_id: str,
    *,
    action: str | None = None,
) -> list[AuditLog]:
    query = select(AuditLog).where(AuditLog.organization_id == UUID(organization_id))
    if action:
        query = query.where(AuditLog.action == action)
    result = await db.execute(query.order_by(AuditLog.created_at))
    return list(result.scalars())


def scan_payload(tenant: SimTenant, profile: str = "safe") -> dict[str, Any]:
    return {
        "project_id": tenant.project_id,
        "domain_id": tenant.domain_id,
        "scan_profile": profile,
        "target_url": tenant.target_url,
        "authorization_accepted": True,
    }
