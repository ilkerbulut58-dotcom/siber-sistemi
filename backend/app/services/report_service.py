"""Scan report generation (HTML, PDF, JSON)."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.i18n.report_strings import (
    FINDING_STATUS_LABELS,
    PROFILE_LABELS,
    SCAN_REPORT_LABELS,
    SEVERITY_LABELS,
    STATUS_LABELS,
    Locale,
    normalize_locale,
    scan_risk_summary,
)
from app.models.scan import ScanJob, ScanStatus
from app.services.finding_service import FindingService
from app.services.pdf_utils import html_to_pdf
from app.services.report_finding_localization import localize_findings_for_report
from app.services.scan_service import ScanService

logger = logging.getLogger(__name__)

ReportFormat = Literal["html", "pdf", "json"]

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


class ReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._jinja = Environment(
            loader=FileSystemLoader(Path(__file__).resolve().parent.parent / "templates"),
            autoescape=select_autoescape(["html"]),
        )

    async def build(
        self,
        organization_id: UUID,
        scan_id: UUID,
        report_format: ReportFormat,
        locale: str | None = "tr",
    ) -> tuple[bytes, str, str]:
        loc = normalize_locale(locale)
        scan = await ScanService(self.db).get(organization_id, scan_id)
        status = scan.status.value if hasattr(scan.status, "value") else str(scan.status)
        if status != ScanStatus.COMPLETED.value:
            raise AppError(
                "SCAN_NOT_READY",
                "Report is available only for completed scans.",
                status_code=400,
            )

        findings = await FindingService(self.db).list_for_org(
            organization_id,
            scan_id=scan_id,
        )
        findings_sorted = sorted(
            findings,
            key=lambda f: (SEVERITY_ORDER.get(f.severity, 99), f.title),
        )
        localized_findings = localize_findings_for_report(findings_sorted, loc)

        if report_format == "json":
            return self._build_json(scan, localized_findings, loc)

        html = self._render_html(scan, localized_findings, loc)
        if report_format == "html":
            filename = self._filename(scan, "html")
            return html.encode("utf-8"), "text/html; charset=utf-8", filename

        pdf_bytes = html_to_pdf(html)
        filename = self._filename(scan, "pdf")
        return pdf_bytes, "application/pdf", filename

    def _render_html(self, scan: ScanJob, findings, locale: Locale) -> str:
        severity_counts: dict[str, int] = {}
        for finding in findings:
            severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1

        template = self._jinja.get_template("scan_report.html")
        status_key = scan.status.value if hasattr(scan.status, "value") else str(scan.status)
        return template.render(
            locale=locale,
            labels=SCAN_REPORT_LABELS[locale],
            scan=scan,
            findings=findings,
            profile_label=PROFILE_LABELS[locale].get(scan.scan_profile, scan.scan_profile),
            status_label=STATUS_LABELS[locale].get(status_key, status_key),
            severity_labels=SEVERITY_LABELS[locale],
            status_labels=FINDING_STATUS_LABELS[locale],
            severity_counts=severity_counts,
            risk_summary=scan_risk_summary(locale, severity_counts),
            completed_at=(
                scan.completed_at.astimezone(UTC).strftime("%d.%m.%Y %H:%M UTC")
                if scan.completed_at
                else "—"
            ),
            generated_at=datetime.now(UTC).strftime("%d.%m.%Y %H:%M UTC"),
        )

    def _build_json(
        self,
        scan: ScanJob,
        findings,
        locale: Locale,
    ) -> tuple[bytes, str, str]:
        severity_counts: dict[str, int] = {}
        for finding in findings:
            severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1

        status_key = scan.status.value if hasattr(scan.status, "value") else str(scan.status)
        payload = {
            "locale": locale,
            "scan": {
                "id": str(scan.id),
                "target_url": scan.target_url,
                "scan_profile": scan.scan_profile,
                "profile_label": PROFILE_LABELS[locale].get(scan.scan_profile, scan.scan_profile),
                "status": status_key,
                "status_label": STATUS_LABELS[locale].get(status_key, status_key),
                "findings_count": scan.findings_count,
                "started_at": scan.started_at.isoformat() if scan.started_at else None,
                "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
            },
            "summary": {
                "risk_summary": scan_risk_summary(locale, severity_counts),
                "severity_counts": severity_counts,
            },
            "findings": [
                {
                    "id": str(f.id),
                    "title": f.title,
                    "severity": f.severity,
                    "severity_label": SEVERITY_LABELS[locale].get(f.severity, f.severity),
                    "status": f.status,
                    "status_label": FINDING_STATUS_LABELS[locale].get(f.status, f.status),
                    "description": f.description,
                    "risk_explanation": f.risk_explanation,
                    "affected_url": f.affected_url,
                    "remediation": f.remediation,
                    "remediation_steps": f.remediation_steps,
                    "config_file_paths": f.config_file_paths,
                    "config_snippet": f.config_snippet,
                    "source_tool": f.source_tool,
                    "source_rule_id": f.source_rule_id,
                    "risk_score": f.risk_score,
                    "ai_summary": f.ai_summary,
                    "ai_remediation": f.ai_remediation,
                    "ai_confidence_label": f.ai_confidence_label,
                }
                for f in findings
            ],
        }
        content = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        return content, "application/json; charset=utf-8", self._filename(scan, "json")

    @staticmethod
    def _risk_summary(counts: dict[str, int]) -> str:
        """Backward-compatible helper for tests."""
        return scan_risk_summary("tr", counts)

    @staticmethod
    def _filename(scan: ScanJob, extension: str) -> str:
        host = scan.target_url.replace("https://", "").replace("http://", "").split("/")[0]
        safe_host = "".join(c if c.isalnum() or c in ".-" else "_" for c in host)
        date_part = scan.completed_at.strftime("%Y%m%d") if scan.completed_at else "report"
        return f"siber-{safe_host}-{date_part}.{extension}"
