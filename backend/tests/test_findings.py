"""Finding endpoint tests."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def _context(client: AsyncClient) -> tuple[dict, dict, dict, dict]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "findings@example.com", "password": "SecurePass123!", "full_name": "F"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['data']['tokens']['access_token']}"}
    org = (
        await client.post("/api/v1/organizations", json={"name": "Findings Org"}, headers=headers)
    ).json()["data"]
    project = (
        await client.post(
            f"/api/v1/organizations/{org['id']}/projects",
            json={"name": "Site", "environment": "staging"},
            headers=headers,
        )
    ).json()["data"]

    with patch("app.services.domain_service.hostname_resolves", return_value=True):
        domain = (
            await client.post(
                f"/api/v1/organizations/{org['id']}/projects/{project['id']}/domains",
                json={"hostname": "find.example.com", "method": "dns_txt"},
                headers=headers,
            )
        ).json()["data"]

    with patch("app.services.domain_service.run_verification", new_callable=AsyncMock, return_value=True):
        await client.post(
            f"/api/v1/organizations/{org['id']}/projects/{project['id']}/domains/{domain['id']}/verify",
            headers=headers,
        )

    return headers, org, project, domain


@pytest.mark.asyncio
@patch(
    "app.scanners.orchestrator.run_scan_for_profile",
    new_callable=AsyncMock,
)
async def test_scan_produces_findings(mock_scan: AsyncMock, client: AsyncClient) -> None:
    from app.scanners.base import RawFinding

    mock_scan.return_value = [
        RawFinding(
            source_tool="passive_http",
            source_rule_id="missing-header-x-frame-options",
            title="Missing X-Frame-Options header",
            description="test",
            severity="medium",
            affected_url="https://find.example.com",
            remediation="Set header",
        )
    ]
    headers, org, project, domain = await _context(client)

    scan = (
        await client.post(
            f"/api/v1/organizations/{org['id']}/scans",
            json={
                "project_id": project["id"],
                "domain_id": domain["id"],
                "scan_profile": "safe",
                "target_url": "https://find.example.com",
                "authorization_accepted": True,
            },
            headers=headers,
        )
    ).json()["data"]

    from app.core.database import async_session_factory
    from app.services.scan_service import run_scan_job

    await run_scan_job(scan["id"], async_session_factory)

    findings = await client.get(
        f"/api/v1/organizations/{org['id']}/findings?scan_id={scan['id']}",
        headers=headers,
    )
    assert findings.status_code == 200
    body = findings.json()["data"]
    assert len(body) >= 1
    assert body[0]["source_tool"] == "passive_http"
