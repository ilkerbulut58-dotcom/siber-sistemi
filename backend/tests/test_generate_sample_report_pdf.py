"""Generate sample PDF artifacts for delivery (synthetic fixture scan)."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models.finding import Finding, FindingSeverity, FindingStatus
from app.models.scan import ScanJob, ScanStatus
from app.services.report_service import ReportService

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "reports" / "samples"


@pytest.mark.asyncio
async def test_write_sample_pdf_tr_and_de(client: AsyncClient, db_session) -> None:
    from app.models.domain import Domain
    from app.models.organization import Organization
    from app.models.project import Project
    from app.models.user import User

    user = User(
        id=uuid4(),
        email="report-fixture@example.com",
        password_hash="x",
        full_name="Fixture",
        is_active=True,
        is_email_verified=True,
    )
    org = Organization(id=uuid4(), name="Fixture Org", slug="fixture-org", owner_id=user.id)
    project = Project(
        id=uuid4(),
        organization_id=org.id,
        name="Fixture",
        environment="staging",
        is_active=True,
    )
    domain = Domain(
        id=uuid4(),
        organization_id=org.id,
        project_id=project.id,
        hostname="fixture.test.example",
        is_verified=True,
        verification_method="dns_txt",
    )
    scan = ScanJob(
        id=uuid4(),
        organization_id=org.id,
        project_id=project.id,
        domain_id=domain.id,
        initiated_by=user.id,
        scan_profile="safe",
        target_url="https://fixture.test.example/",
        status=ScanStatus.COMPLETED.value,
        findings_count=2,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        authorization_source="dns_verification",
        scope_config={
            "planned_scope": {
                "scan_profile": "safe",
                "authorization_source": "dns_verification",
                "planned_scanners": ["passive_http", "sensitive_data", "zap", "nuclei"],
            },
            "executed_telemetry": {
                "findings_persisted": 2,
                "scanner_runs_completed": 4,
                "scanner_runs_failed_or_timed_out": 0,
                "unique_urls_scanned_sum": None,
                "scanner_runs": [
                    {
                        "scanner_id": "passive_http",
                        "status": "completed",
                        "finding_count": 2,
                        "execution_seconds": 0.8,
                        "control_summary_tr": "HTTP/TLS",
                        "control_summary_de": "HTTP/TLS",
                    },
                    {
                        "scanner_id": "nuclei",
                        "status": "completed",
                        "finding_count": 0,
                        "execution_seconds": 2.1,
                        "control_summary_tr": "Nuclei",
                        "control_summary_de": "Nuclei",
                    },
                ],
            },
        },
    )
    finding = Finding(
        id=uuid4(),
        organization_id=org.id,
        project_id=project.id,
        scan_job_id=scan.id,
        source_tool="passive_http",
        source_rule_id="x-powered-by-disclosure",
        title="X-Powered-By disclosure",
        severity=FindingSeverity.INFO.value,
        status=FindingStatus.OPEN.value,
        affected_url=scan.target_url,
        evidence={
            "evidence_type": "http_header",
            "header_name": "X-Powered-By",
            "header_value": "PHP/8.2.0",
            "x_powered_by": "PHP/8.2.0",
        },
        fingerprint="abc123",
    )
    db_session.add_all([user, org, project, domain, scan, finding])
    await db_session.commit()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    banner = (
        "TEST VERİSİ — canlı site değerlendirmesi değildir / "
        "TESTDATEN — keine Live-Bewertung\n"
    )
    for locale, name in (("tr", "sample-scan-report-tr.pdf"), ("de", "sample-scan-report-de.pdf")):
        content, _, _ = await ReportService(db_session).build(org.id, scan.id, "pdf", locale)
        path = OUTPUT_DIR / name
        path.write_bytes(content)
        meta = OUTPUT_DIR / f"{name}.meta.txt"
        meta.write_text(banner + f"locale={locale}\nscan_id={scan.id}\n", encoding="utf-8")
    assert (OUTPUT_DIR / "sample-scan-report-tr.pdf").stat().st_size > 500
