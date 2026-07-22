"""Mobile application security report generation (HTML, PDF, JSON)."""

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
from app.mobile.services.mobile_service import MobileService
from app.models.finding import Finding
from app.models.mobile_application import MobileAnalysisStatus
from app.services.finding_service import FindingService
from app.services.pdf_utils import html_to_pdf

logger = logging.getLogger(__name__)

ReportFormat = Literal["html", "pdf", "json"]

SEVERITY_LABELS = {
    "critical": "Kritik",
    "high": "Yüksek",
    "medium": "Orta",
    "low": "Düşük",
    "info": "Bilgi",
}

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


class MobileReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._jinja = Environment(
            loader=FileSystemLoader(Path(__file__).resolve().parent.parent / "templates"),
            autoescape=select_autoescape(["html"]),
        )

    async def build(
        self,
        organization_id: UUID,
        app_id: UUID,
        report_format: ReportFormat,
    ) -> tuple[bytes, str, str]:
        app = await MobileService(self.db).get(organization_id, app_id)
        status = (
            app.analysis_status.value
            if hasattr(app.analysis_status, "value")
            else str(app.analysis_status)
        )
        if status != MobileAnalysisStatus.COMPLETED.value:
            raise AppError(
                "MOBILE_ANALYSIS_NOT_READY",
                "Report is available only for completed mobile analyses.",
                status_code=400,
            )

        findings = await FindingService(self.db).list_for_org(
            organization_id,
            project_id=app.project_id,
            mobile_application_id=app.id,
            asset_type="mobile",
        )
        findings_sorted = sorted(
            findings,
            key=lambda f: (SEVERITY_ORDER.get(f.severity, 99), f.title),
        )

        if report_format == "json":
            return self._build_json(app, findings_sorted)

        html = self._render_html(app, findings_sorted)
        if report_format == "html":
            return html.encode("utf-8"), "text/html; charset=utf-8", self._filename(app, "html")

        pdf_bytes = html_to_pdf(html)
        return pdf_bytes, "application/pdf", self._filename(app, "pdf")

    def _render_html(self, app, findings: list[Finding]) -> str:
        severity_counts: dict[str, int] = {}
        masvs_categories: dict[str, int] = {}
        for finding in findings:
            severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1
            if finding.masvs_category:
                masvs_categories[finding.masvs_category] = (
                    masvs_categories.get(finding.masvs_category, 0) + 1
                )

        template = self._jinja.get_template("mobile_report.html")
        return template.render(
            app=app,
            findings=findings,
            severity_labels=SEVERITY_LABELS,
            severity_counts=severity_counts,
            masvs_categories=masvs_categories,
            risk_summary=self._risk_summary(severity_counts, app.security_score),
            analyzed_at=(
                app.analyzed_at.astimezone(UTC).strftime("%d.%m.%Y %H:%M UTC")
                if app.analyzed_at
                else "—"
            ),
            generated_at=datetime.now(UTC).strftime("%d.%m.%Y %H:%M UTC"),
        )

    def _build_json(self, app, findings: list[Finding]) -> tuple[bytes, str, str]:
        severity_counts: dict[str, int] = {}
        masvs_categories: dict[str, int] = {}
        for finding in findings:
            severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1
            if finding.masvs_category:
                masvs_categories[finding.masvs_category] = (
                    masvs_categories.get(finding.masvs_category, 0) + 1
                )

        payload = {
            "application": {
                "id": str(app.id),
                "application_name": app.application_name,
                "package_name": app.package_name,
                "platform": app.platform,
                "version_name": app.version_name,
                "version_code": app.version_code,
                "sha256": app.sha256,
                "file_size": app.file_size,
                "original_filename": app.original_filename,
                "security_score": app.security_score,
                "findings_count": app.findings_count,
                "analyzed_at": app.analyzed_at.isoformat() if app.analyzed_at else None,
            },
            "summary": {
                "risk_summary": self._risk_summary(severity_counts, app.security_score),
                "severity_counts": severity_counts,
                "masvs_categories": masvs_categories,
            },
            "scope": {
                "method": "static_apk_analysis",
                "limitations": [
                    "No dynamic runtime analysis or code execution",
                    "Binary manifest parsing not performed (text-based static checks)",
                    "iOS IPA not supported in this release",
                ],
            },
            "findings": [
                {
                    "id": str(f.id),
                    "title": f.title,
                    "severity": f.severity,
                    "status": f.status,
                    "description": f.description,
                    "affected_component": f.affected_component,
                    "masvs_category": f.masvs_category,
                    "remediation": f.remediation,
                    "risk_score": f.risk_score,
                    "source_tool": f.source_tool,
                    "source_rule_id": f.source_rule_id,
                }
                for f in findings
            ],
            "generated_at": datetime.now(UTC).isoformat(),
        }
        content = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        return content, "application/json; charset=utf-8", self._filename(app, "json")

    @staticmethod
    def _risk_summary(counts: dict[str, int], security_score: float | None) -> str:
        if (counts.get("critical") or 0) > 0 or (counts.get("high") or 0) > 0:
            return "Yüksek öncelikli mobil güvenlik bulguları tespit edildi."
        if (counts.get("medium") or 0) > 0:
            return "Orta seviye mobil güvenlik iyileştirmeleri önerilir."
        if security_score is not None and security_score >= 80:
            return "Mobil güvenlik durumu genel olarak iyi görünüyor."
        return "Kritik mobil bulgu tespit edilmedi; periyodik analiz önerilir."

    @staticmethod
    def _filename(app, extension: str) -> str:
        pkg = app.package_name or app.original_filename or "mobile-app"
        safe = "".join(c if c.isalnum() or c in ".-" else "_" for c in pkg)
        date_part = app.analyzed_at.strftime("%Y%m%d") if app.analyzed_at else "report"
        return f"siber-mobile-{safe}-{date_part}.{extension}"
