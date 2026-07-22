"""Report generation tests."""

from uuid import UUID

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.models.scan import ScanJob, ScanStatus
from app.services.report_service import ReportService
from tests.test_scans import _verified_domain


@pytest.mark.asyncio
async def test_report_requires_completed_scan(client: AsyncClient, db_session) -> None:
    headers, org, ctx = await _verified_domain(client, "report-fail@example.com")

    with patch("app.api.v1.scans.dispatch_scan_job", new_callable=AsyncMock):
        create = await client.post(
            f"/api/v1/organizations/{org['id']}/scans",
            json={
                "project_id": ctx["project"]["id"],
                "domain_id": ctx["domain"]["id"],
                "scan_profile": "safe",
                "target_url": "https://scan.example.com",
                "authorization_accepted": True,
            },
            headers=headers,
        )
    scan_id = create.json()["data"]["id"]

    response = await client.get(
        f"/api/v1/organizations/{org['id']}/scans/{scan_id}/report?format=html",
        headers=headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_report_html_and_json(client: AsyncClient, db_session) -> None:
    headers, org, ctx = await _verified_domain(client, "report-ok@example.com")

    with patch("app.api.v1.scans.dispatch_scan_job", new_callable=AsyncMock):
        create = await client.post(
            f"/api/v1/organizations/{org['id']}/scans",
            json={
                "project_id": ctx["project"]["id"],
                "domain_id": ctx["domain"]["id"],
                "scan_profile": "safe",
                "target_url": "https://scan.example.com",
                "authorization_accepted": True,
            },
            headers=headers,
        )
    scan_id = create.json()["data"]["id"]

    scan = await db_session.get(ScanJob, UUID(scan_id))
    assert scan is not None
    scan.status = ScanStatus.COMPLETED
    scan.findings_count = 0
    await db_session.commit()

    html = await client.get(
        f"/api/v1/organizations/{org['id']}/scans/{scan_id}/report?format=html",
        headers=headers,
    )
    assert html.status_code == 200
    assert "text/html" in html.headers["content-type"]
    assert "SIBER" in html.text

    json_report = await client.get(
        f"/api/v1/organizations/{org['id']}/scans/{scan_id}/report?format=json",
        headers=headers,
    )
    assert json_report.status_code == 200
    assert json_report.json()["scan"]["id"] == scan_id


@pytest.mark.asyncio
async def test_report_service_risk_summary() -> None:
    assert "Yüksek" in ReportService._risk_summary({"high": 1})
    assert "Önemli bir sorun" in ReportService._risk_summary({})
