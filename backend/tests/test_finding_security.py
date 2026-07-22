"""Finding security tests: IDOR, evidence masking, risk breakdown."""

from __future__ import annotations

import io
import zipfile
from datetime import UTC, datetime
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.models.finding import Finding, FindingStatus
from app.services.finding_response_builder import to_finding_response


def _minimal_apk() -> bytes:
    manifest = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.security.test"
    android:versionCode="1"
    android:versionName="1.0">
    <application android:debuggable="true" />
</manifest>"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("AndroidManifest.xml", manifest)
        zf.writestr("classes.dex", b"dex\n035\x00")
    return buffer.getvalue()


async def _org_with_project(client: AsyncClient, email: str, org_name: str) -> tuple[dict, dict, dict]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePass123!", "full_name": email.split("@")[0]},
    )
    headers = {"Authorization": f"Bearer {reg.json()['data']['tokens']['access_token']}"}
    org = (
        await client.post("/api/v1/organizations", json={"name": org_name}, headers=headers)
    ).json()["data"]
    project = (
        await client.post(
            f"/api/v1/organizations/{org['id']}/projects",
            json={"name": "Sec Project", "environment": "staging"},
            headers=headers,
        )
    ).json()["data"]
    return headers, org, project


async def _run_mobile_analysis(app_id, **kwargs) -> None:
    from app.mobile.services.mobile_service import MobileService

    async with async_session_factory() as session:
        await MobileService(session).run_analysis(app_id)


@pytest.mark.asyncio
async def test_finding_idor_cross_org(client: AsyncClient, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MOBILE_STORAGE_PATH", str(tmp_path / "mobile-idor"))
    get_settings.cache_clear()

    headers_a, org_a, project_a = await _org_with_project(client, "orga@example.com", "Org A")
    headers_b, org_b, _project_b = await _org_with_project(client, "orgb@example.com", "Org B")

    with patch("app.api.v1.mobile.dispatch_mobile_analysis", new=_run_mobile_analysis):
        upload = await client.post(
            f"/api/v1/organizations/{org_a['id']}/mobile/applications",
            headers=headers_a,
            data={"project_id": project_a["id"], "authorization_accepted": "true"},
            files={"file": ("app.apk", _minimal_apk(), "application/vnd.android.package-archive")},
        )
    assert upload.status_code == 201
    app_id = upload.json()["data"]["id"]

    findings_resp = await client.get(
        f"/api/v1/organizations/{org_a['id']}/mobile/applications/{app_id}/findings",
        headers=headers_a,
    )
    assert findings_resp.status_code == 200
    findings = findings_resp.json()["data"]
    assert findings
    finding_id = findings[0]["id"]

    cross_org_get = await client.get(
        f"/api/v1/organizations/{org_b['id']}/findings/{finding_id}",
        headers=headers_b,
    )
    assert cross_org_get.status_code == 404

    cross_org_mobile = await client.get(
        f"/api/v1/organizations/{org_b['id']}/mobile/applications/{app_id}",
        headers=headers_b,
    )
    assert cross_org_mobile.status_code == 404


@pytest.mark.asyncio
async def test_evidence_masking_in_api_response(client: AsyncClient, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MOBILE_STORAGE_PATH", str(tmp_path / "mobile-evidence"))
    get_settings.cache_clear()

    headers, org, project = await _org_with_project(client, "evidence@example.com", "Evidence Org")

    secret_apk = _minimal_apk()
    with patch("app.api.v1.mobile.dispatch_mobile_analysis", new=_run_mobile_analysis):
        upload = await client.post(
            f"/api/v1/organizations/{org['id']}/mobile/applications",
            headers=headers,
            data={"project_id": project["id"], "authorization_accepted": "true"},
            files={"file": ("app.apk", secret_apk, "application/vnd.android.package-archive")},
        )
    app_id = upload.json()["data"]["id"]

    async with async_session_factory() as session:
        now = datetime.now(UTC)
        finding = Finding(
            id=uuid4(),
            organization_id=UUID(org["id"]),
            project_id=UUID(project["id"]),
            scan_job_id=None,
            mobile_application_id=UUID(app_id),
            source_tool="mobile_static",
            source_rule_id="test-secret-leak",
            title="Synthetic secret finding",
            description="Bearer sk-live-abcdefghijklmnopqrstuvwxyz123456",
            affected_url="com.security.test",
            severity="high",
            confidence="high",
            fingerprint="abc123" * 10 + "abcd",
            status=FindingStatus.OPEN,
            asset_type="mobile",
            platform="android",
            first_seen_at=now,
            last_seen_at=now,
            evidence={
                "authorization": "Bearer sk-secret-token-value",
                "api_key": "AKIAIOSFODNN7EXAMPLE",
                "headers": {"Cookie": "sessionid=supersecret", "Accept": "application/json"},
            },
        )
        session.add(finding)
        await session.commit()

    response = await client.get(
        f"/api/v1/organizations/{org['id']}/findings/{finding.id}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["evidence"]["authorization"] == "[REDACTED]"
    assert data["evidence"]["api_key"] == "[REDACTED]"
    assert data["evidence"]["headers"]["Cookie"] == "[REDACTED]"
    assert "sk-live" not in (data["description"] or "")


def test_risk_breakdown_in_finding_response() -> None:
    now = datetime.now(UTC)
    finding = Finding(
        id=uuid4(),
        organization_id=uuid4(),
        project_id=uuid4(),
        scan_job_id=None,
        source_tool="mobile_static",
        source_rule_id="mobile-debuggable",
        title="Application is debuggable",
        description="debuggable enabled",
        affected_url="com.example.app",
        severity="high",
        confidence="high",
        correlation_key="mobile-debuggable",
        risk_score=72.5,
        source_tools=["mobile_static"],
        verification_status="verified",
        fingerprint="deadbeef" * 8,
        status=FindingStatus.OPEN,
        asset_type="mobile",
        platform="android",
        masvs_category="MASVS-RESILIENCE-1",
        first_seen_at=now,
        last_seen_at=now,
        created_at=now,
        updated_at=now,
    )
    response = to_finding_response(finding)
    assert response.risk_breakdown is not None
    assert response.risk_breakdown.total == 72.5
    assert len(response.risk_breakdown.items) >= 1
    assert response.asset_type == "mobile"
    assert response.platform == "android"
