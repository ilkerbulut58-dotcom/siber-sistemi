"""Report finding localization tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.models.finding import Finding, FindingStatus
from app.models.scan import ScanJob, ScanStatus
from app.services.report_finding_localization import localize_finding_for_report
from tests.test_scans import _verified_domain


def test_localize_hsts_finding_german():
    finding = Finding(
        id=uuid4(),
        organization_id=uuid4(),
        project_id=uuid4(),
        scan_job_id=uuid4(),
        source_tool="passive_http",
        source_rule_id="missing-header-strict-transport-security",
        correlation_key="missing-header-strict-transport-security",
        title="HTTPS zorunluluğu (HSTS) ayarı eksik",
        description="Site HTTPS ile açılıyor ancak tarayıcıya kalıcı güvenli bağlantı talimatı verilmiyor.",
        severity="medium",
        fingerprint="abc123" * 10 + "abcd",
        status=FindingStatus.OPEN,
        affected_url="https://example.de/",
        remediation="Yanıta HSTS header ekleyin.",
        risk_explanation="Kullanıcı bir kez HTTP bağlantısına düşerse risk artar.",
        remediation_steps=["Türkçe adım"],
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )
    localized = localize_finding_for_report(finding, "de")
    assert "HSTS" in localized.title
    assert "HTTPS" in localized.title or "HTTPS-Pflicht" in localized.title
    assert localized.risk_explanation
    assert "Kullanıcı" not in localized.risk_explanation
    assert localized.remediation
    assert "Yanıta" not in (localized.remediation or "")
    assert localized.remediation_steps
    assert "Türkçe" not in (localized.remediation_steps or [""])[0]


@pytest.mark.asyncio
async def test_report_html_german_finding_text(client: AsyncClient, db_session) -> None:
    from unittest.mock import AsyncMock, patch

    headers, org, ctx = await _verified_domain(client, "report-de-finding@example.com")

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
    scan.findings_count = 1
    await db_session.commit()

    now = datetime.now(UTC)
    finding = Finding(
        id=uuid4(),
        organization_id=UUID(org["id"]),
        project_id=UUID(ctx["project"]["id"]),
        scan_job_id=UUID(scan_id),
        source_tool="passive_http",
        source_rule_id="missing-header-strict-transport-security",
        correlation_key="missing-header-strict-transport-security",
        title="HTTPS zorunluluğu (HSTS) ayarı eksik",
        description="Türkçe açıklama",
        severity="medium",
        fingerprint="deadbeef" * 8,
        status=FindingStatus.OPEN,
        affected_url="https://scan.example.com/",
        remediation="Yanıta HSTS header ekleyin.",
        risk_explanation="Türkçe risk açıklaması",
        remediation_steps=["Türkçe adım bir"],
        first_seen_at=now,
        last_seen_at=now,
    )
    db_session.add(finding)
    await db_session.commit()

    html = await client.get(
        f"/api/v1/organizations/{org['id']}/scans/{scan_id}/report?format=html&locale=de",
        headers=headers,
    )
    assert html.status_code == 200
    assert "Sicherheits-Scan-Bericht" in html.text
    assert "HTTPS-Pflicht (HSTS) fehlt" in html.text
    assert "Türkçe" not in html.text
    assert "Yanıta" not in html.text

    json_report = await client.get(
        f"/api/v1/organizations/{org['id']}/scans/{scan_id}/report?format=json&locale=de",
        headers=headers,
    )
    assert json_report.status_code == 200
    finding_payload = json_report.json()["findings"][0]
    assert "HTTPS-Pflicht (HSTS) fehlt" in finding_payload["title"]
    assert "Türkçe" not in finding_payload["title"]


def test_localize_csp_wildcard_uses_catalog_not_english_generic():
    finding = Finding(
        id=uuid4(),
        organization_id=uuid4(),
        project_id=uuid4(),
        scan_job_id=uuid4(),
        source_tool="zap",
        source_rule_id="generic.csp-wildcard-directive",
        correlation_key="generic.csp-wildcard-directive",
        title="CSP: Wildcard Directive",
        description="Ensure that your web server is properly configured.",
        severity="medium",
        fingerprint="abc123" * 10 + "abcd",
        status=FindingStatus.OPEN,
        affected_url="https://example.test/",
        remediation="Ensure that your web server, application server, load balancer, etc. is properly configured to set the Content-Security-Policy header.",
        risk_explanation="CSP: Wildcard Directive — Orta önem derecesinde tespit edildi.",
        evidence={
            "evidence_type": "http_header",
            "header_name": "Content-Security-Policy",
            "header_value": "default-src 'self'; img-src https: data: blob:",
        },
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )
    tr = localize_finding_for_report(finding, "tr")
    de = localize_finding_for_report(finding, "de")
    assert "XSS" in (tr.risk_explanation or "")
    assert "doğrulanmış" in (tr.risk_explanation or "").lower() or "bestätig" in (de.risk_explanation or "").lower()
    assert "Ensure that your web server" not in (tr.remediation or "")
    assert tr.remediation_steps
    assert any("yıldız" in step.lower() or "*" in step for step in tr.remediation_steps)
    assert any("https:" in step or "şema" in step.lower() for step in tr.remediation_steps)
    assert "XSS" in (de.risk_explanation or "")
    assert "Ensure that your web server" not in (de.remediation or "")


def test_localize_cache_control_not_data_leak():
    finding = Finding(
        id=uuid4(),
        organization_id=uuid4(),
        project_id=uuid4(),
        scan_job_id=uuid4(),
        source_tool="zap",
        source_rule_id="generic.re-examine-cache-control-directives",
        title="Re-examine Cache-control Directives",
        description="For secure content, ensure no-cache.",
        severity="info",
        fingerprint="feedbeef" * 8,
        status=FindingStatus.OPEN,
        affected_url="https://example.test/",
        remediation='For secure content, ensure the cache-control HTTP header is set with "no-cache, no-store, must-revalidate".',
        risk_explanation="Re-examine Cache-control Directives — Bilgi önem derecesinde tespit edildi.",
        evidence={
            "evidence_type": "http_header",
            "header_name": "Cache-Control",
            "header_value": "s-maxage=31536000",
        },
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )
    tr = localize_finding_for_report(finding, "tr")
    assert "s-maxage" in (tr.risk_explanation or "") + " ".join(tr.remediation_steps or [])
    assert "sızıntı" in ((tr.risk_explanation or "") + (tr.remediation or "")).lower()
    assert "For secure content" not in (tr.remediation or "")
