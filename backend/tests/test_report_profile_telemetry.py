"""Profile labels, scanner telemetry, and remediation context in reports."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.models.finding import Finding, FindingSeverity, FindingStatus
from app.models.scan import ScanJob, ScanStatus
from app.scanners.orchestrator import run_scan_for_profile
from app.services.report_remediation_context import contextual_remediation
from app.services.report_scope import build_report_scope_context, profile_label


@pytest.mark.asyncio
async def test_code_profile_runs_four_scanners_not_nuclei() -> None:
    with (
        patch("app.scanners.orchestrator.run_passive_http_scan", new_callable=AsyncMock, return_value=[]),
        patch("app.scanners.orchestrator.scan_sensitive_data", new_callable=AsyncMock, return_value=[]),
        patch("app.scanners.orchestrator.scan_exposed_paths", new_callable=AsyncMock, return_value=[]),
        patch("app.scanners.orchestrator.scan_response_secrets", new_callable=AsyncMock, return_value=[]),
        patch("app.scanners.orchestrator.run_nuclei_scan", new_callable=AsyncMock) as mock_nuclei,
    ):
        await run_scan_for_profile("https://example.com", "code")
    mock_nuclei.assert_not_called()


def test_profile_label_code_not_misleading() -> None:
    assert "Kod / Dosya" not in profile_label("code", "tr")
    assert "HTTP" in profile_label("code", "tr")


def test_report_scope_includes_scanner_rows() -> None:
    scan = ScanJob(
        id=uuid4(),
        organization_id=uuid4(),
        project_id=uuid4(),
        domain_id=uuid4(),
        initiated_by=uuid4(),
        scan_profile="code",
        target_url="https://example.com/",
        status=ScanStatus.COMPLETED.value,
        authorization_source="admin_dns_exempt",
        scope_config={
            "planned_scope": {
                "scan_profile": "code",
                "authorization_source": "admin_dns_exempt",
                "planned_scanners": ["passive_http", "sensitive_data", "exposed_paths", "secrets"],
            },
            "executed_telemetry": {
                "scanner_runs": [
                    {
                        "scanner_id": "passive_http",
                        "status": "completed",
                        "finding_count": 2,
                        "execution_seconds": 1.2,
                        "control_summary_tr": "HTTP/TLS",
                    },
                    {
                        "scanner_id": "nuclei",
                        "status": "not_run",
                        "finding_count": 0,
                        "control_summary_tr": "—",
                    },
                ],
                "scanner_runs_completed": 1,
                "scanner_runs_failed_or_timed_out": 0,
                "code_source_scan_status": "not_supported_no_upload",
            },
        },
    )
    ctx = build_report_scope_context(scan, "tr")
    assert ctx["profile_label"] == profile_label("code", "tr")
    assert "Admin DNS muafiyeti" in ctx["scope_summary_rows"][1]["value"]
    assert len(ctx["scanner_rows"]) == 2
    assert ctx["profile_scope_note"]


def test_server_remediation_without_version() -> None:
    finding = Finding(
        id=uuid4(),
        organization_id=uuid4(),
        project_id=uuid4(),
        scan_job_id=uuid4(),
        source_tool="passive_http",
        source_rule_id="server-disclosure",
        title="Server",
        severity=FindingSeverity.INFO.value,
        status=FindingStatus.OPEN.value,
        evidence={"server": "nginx", "header_value": "nginx"},
    )
    summary, steps, snippet = contextual_remediation(finding, "tr")
    assert summary
    assert steps
    assert snippet is None
    assert any("nginx" in s for s in steps)


def test_xpowered_passenger_not_php_only() -> None:
    finding = Finding(
        id=uuid4(),
        organization_id=uuid4(),
        project_id=uuid4(),
        scan_job_id=uuid4(),
        source_tool="passive_http",
        source_rule_id="x-powered-by-disclosure",
        title="X-Powered-By",
        severity=FindingSeverity.INFO.value,
        status=FindingStatus.OPEN.value,
        evidence={"x_powered_by": "Phusion Passenger(R), PleskLin"},
    )
    _, steps, _ = contextual_remediation(finding, "tr")
    assert steps
    assert any("Passenger" in s or "Plesk" in s for s in steps)
    assert not steps[0].startswith("PHP:")
    assert any("Phusion Passenger" in s for s in steps)


def test_legacy_url_sum_not_shown_as_unique_total() -> None:
    scan = ScanJob(
        id=uuid4(),
        organization_id=uuid4(),
        project_id=uuid4(),
        domain_id=uuid4(),
        initiated_by=uuid4(),
        scan_profile="safe",
        target_url="https://example.test/",
        status=ScanStatus.COMPLETED.value,
        findings_count=7,
        authorization_source="admin_dns_exempt",
        scope_config={
            "planned_scope": {
                "scan_profile": "safe",
                "authorization_source": "admin_dns_exempt",
                "planned_scanners": ["passive_http", "zap", "nuclei"],
            },
            "executed_telemetry": {
                "findings_persisted": 7,
                "unique_urls_scanned_sum": 2,
                "scanner_runs_completed": 4,
                "scanner_runs_failed_or_timed_out": 0,
                "scanner_runs": [
                    {
                        "scanner_id": "zap",
                        "status": "completed",
                        "finding_count": 5,
                        "urls_scanned": 1,
                        "control_summary_tr": "OWASP ZAP pasif/aktif tarama",
                    },
                    {
                        "scanner_id": "nuclei",
                        "status": "completed",
                        "finding_count": 0,
                        "urls_scanned": 1,
                        "control_summary_tr": "Nuclei",
                    },
                    {
                        "scanner_id": "passive_http",
                        "status": "completed",
                        "finding_count": 3,
                    },
                ],
            },
        },
    )
    findings = [
        Finding(
            id=uuid4(),
            organization_id=scan.organization_id,
            project_id=scan.project_id,
            scan_job_id=scan.id,
            source_tool="correlated",
            source_rule_id="server-disclosure",
            title="Server",
            severity=FindingSeverity.INFO.value,
            status=FindingStatus.OPEN.value,
            evidence={"source_count": 1},
        )
        for _ in range(6)
    ]
    findings.append(
        Finding(
            id=uuid4(),
            organization_id=scan.organization_id,
            project_id=scan.project_id,
            scan_job_id=scan.id,
            source_tool="zap",
            source_rule_id="generic.csp-wildcard-directive",
            title="CSP: Wildcard Directive",
            severity=FindingSeverity.MEDIUM.value,
            status=FindingStatus.OPEN.value,
            evidence={"source_count": 2},
        )
    )
    ctx = build_report_scope_context(scan, "tr", findings=findings)
    url_row = next(r for r in ctx["scope_summary_rows"] if r["label"].endswith("URL"))
    assert url_row["value"] != "2"
    assert "benzersiz toplam ölçülmedi" in url_row["value"]
    assert "zap 1" in url_row["value"]
    assert "nuclei 1" in url_row["value"]
    finding_row = next(r for r in ctx["scope_summary_rows"] if r["label"].endswith("bulgu"))
    assert "8 ham kaynak" in finding_row["value"]
    assert "7 benzersiz" in finding_row["value"]
    zap_row = next(r for r in ctx["scanner_rows"] if r["name"] == "zap")
    assert "kaydedilmedi" in zap_row["controls"]
    assert "pasif/aktif tarama" not in zap_row["controls"]
