"""Mobile application security business logic."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.risk_engine import RISK_MODEL_VERSION, build_risk_breakdown, calculate_risk_score
from app.analysis.types import AnalyzedFinding
from app.core.exceptions import AppError
from app.mobile.analyzers.android_static import AndroidStaticAnalyzer
from app.mobile.analyzers.base import MobileFinding
from app.mobile.storage import (
    AsyncUpload,
    delete_mobile_artifact,
    finalize_staged_artifact,
    resolve_artifact_path,
    stage_mobile_upload,
    store_mobile_artifact,
)
from app.models.mobile_application import MobileAnalysisStatus, MobileApplication
from app.models.user import User
from app.schemas.mobile import MobileReportSummary
from app.services.audit_service import log_audit_event
from app.services.finding_service import FindingService
from app.services.project_service import ProjectService

logger = logging.getLogger(__name__)


class MobileService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upload_apk(
        self,
        organization_id: UUID,
        project_id: UUID,
        *,
        filename: str,
        data: bytes,
        environment: str,
        actor: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[MobileApplication, bool]:
        await ProjectService(self.db).get(organization_id, project_id)

        stored = store_mobile_artifact(organization_id, filename, data)
        duplicate = await self._find_duplicate(organization_id, stored.sha256)
        if duplicate is not None:
            delete_mobile_artifact(organization_id, stored.stored_filename)
            await log_audit_event(
                self.db,
                action="mobile.upload.duplicate",
                user_id=actor.id,
                organization_id=organization_id,
                resource_type="mobile_application",
                resource_id=duplicate.id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"sha256": stored.sha256, "existing_id": str(duplicate.id)},
            )
            return duplicate, True

        app = MobileApplication(
            organization_id=organization_id,
            project_id=project_id,
            platform="android",
            environment=environment,
            original_filename=stored.original_filename,
            stored_filename=stored.stored_filename,
            file_size=stored.file_size,
            sha256=stored.sha256,
            created_by=actor.id,
            analysis_status=MobileAnalysisStatus.QUEUED,
        )
        self.db.add(app)
        await self.db.flush()

        await log_audit_event(
            self.db,
            action="mobile.upload.completed",
            user_id=actor.id,
            organization_id=organization_id,
            resource_type="mobile_application",
            resource_id=app.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "filename": app.original_filename,
                "sha256": app.sha256,
                "file_size": app.file_size,
            },
        )
        return app, False

    async def upload_apk_stream(
        self,
        organization_id: UUID,
        project_id: UUID,
        *,
        filename: str,
        upload: AsyncUpload,
        environment: str,
        actor: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[MobileApplication, bool]:
        """Validate and persist an APK without loading it wholly into API memory."""
        await ProjectService(self.db).get(organization_id, project_id)
        staged = await stage_mobile_upload(organization_id, filename, upload)
        stored = None
        try:
            duplicate = await self._find_duplicate(organization_id, staged.sha256)
            if duplicate is not None:
                staged.staging_path.unlink(missing_ok=True)
                await log_audit_event(
                    self.db,
                    action="mobile.upload.duplicate",
                    user_id=actor.id,
                    organization_id=organization_id,
                    resource_type="mobile_application",
                    resource_id=duplicate.id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"sha256": staged.sha256, "existing_id": str(duplicate.id)},
                )
                return duplicate, True

            stored = finalize_staged_artifact(organization_id, staged)
            app = MobileApplication(
                organization_id=organization_id,
                project_id=project_id,
                platform="android",
                environment=environment,
                original_filename=stored.original_filename,
                stored_filename=stored.stored_filename,
                file_size=stored.file_size,
                sha256=stored.sha256,
                created_by=actor.id,
                analysis_status=MobileAnalysisStatus.QUEUED,
            )
            self.db.add(app)
            await self.db.flush()
            await log_audit_event(
                self.db,
                action="mobile.upload.completed",
                user_id=actor.id,
                organization_id=organization_id,
                resource_type="mobile_application",
                resource_id=app.id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "filename": app.original_filename,
                    "sha256": app.sha256,
                    "file_size": app.file_size,
                },
            )
            return app, False
        except Exception:
            staged.staging_path.unlink(missing_ok=True)
            if stored is not None:
                delete_mobile_artifact(organization_id, stored.stored_filename)
            raise

    async def _find_duplicate(
        self, organization_id: UUID, sha256: str
    ) -> MobileApplication | None:
        result = await self.db.execute(
            select(MobileApplication).where(
                MobileApplication.organization_id == organization_id,
                MobileApplication.sha256 == sha256,
            )
        )
        return result.scalar_one_or_none()

    async def get(self, organization_id: UUID, app_id: UUID) -> MobileApplication:
        result = await self.db.execute(
            select(MobileApplication).where(
                MobileApplication.id == app_id,
                MobileApplication.organization_id == organization_id,
            )
        )
        app = result.scalar_one_or_none()
        if app is None:
            raise AppError("NOT_FOUND", "Mobile application not found.", status_code=404)
        return app

    async def list_for_org(
        self,
        organization_id: UUID,
        *,
        project_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MobileApplication]:
        query = select(MobileApplication).where(
            MobileApplication.organization_id == organization_id
        )
        if project_id:
            query = query.where(MobileApplication.project_id == project_id)
        query = query.order_by(MobileApplication.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars())

    async def run_analysis(self, app_id: UUID) -> None:
        result = await self.db.execute(
            select(MobileApplication).where(MobileApplication.id == app_id)
        )
        app = result.scalar_one_or_none()
        if app is None:
            logger.error("Mobile app %s not found for analysis", app_id)
            return

        if app.analysis_status in (
            MobileAnalysisStatus.COMPLETED,
            MobileAnalysisStatus.FAILED,
        ):
            return

        app.analysis_status = MobileAnalysisStatus.RUNNING
        await self.db.commit()

        try:
            artifact_path = resolve_artifact_path(app.organization_id, app.stored_filename)
            analysis = AndroidStaticAnalyzer().analyze(artifact_path)

            app.application_name = analysis.application_name or app.application_name
            app.package_name = analysis.package_name or app.package_name
            app.version_name = analysis.version_name or app.version_name
            app.version_code = analysis.version_code or app.version_code
            app.analysis_summary = analysis.summary

            analyzed = [_to_analyzed_finding(app, item) for item in analysis.findings]
            finding_service = FindingService(self.db)
            saved = await finding_service.persist_mobile_findings(
                organization_id=app.organization_id,
                project_id=app.project_id,
                mobile_application_id=app.id,
                analyzed_findings=analyzed,
            )

            app.findings_count = len(saved)
            app.security_score = _compute_security_score(saved)
            app.analysis_status = MobileAnalysisStatus.COMPLETED
            app.analyzed_at = datetime.now(UTC)
            app.error_log = None
            await self.db.commit()
            from app.services.benchmark_run_service import BenchmarkRunService

            await BenchmarkRunService(self.db).complete_for_mobile(app)
            await self.db.commit()
            logger.info("Mobile analysis completed for %s (%s findings)", app_id, len(saved))
        except Exception as exc:
            logger.exception("Mobile analysis failed for %s", app_id)
            await self.db.rollback()
            result = await self.db.execute(
                select(MobileApplication).where(MobileApplication.id == app_id)
            )
            app = result.scalar_one()
            app.analysis_status = MobileAnalysisStatus.FAILED
            app.error_log = str(exc)
            app.analyzed_at = datetime.now(UTC)
            await self.db.commit()
        finally:
            try:
                delete_mobile_artifact(app.organization_id, app.stored_filename)
            except Exception:
                logger.exception("Unable to clean up mobile artifact for %s", app_id)

    async def build_report(
        self, organization_id: UUID, app_id: UUID
    ) -> MobileReportSummary:
        app = await self.get(organization_id, app_id)
        findings = await FindingService(self.db).list_for_org(
            organization_id,
            project_id=app.project_id,
            mobile_application_id=app.id,
            asset_type="mobile",
        )
        severity_counts: dict[str, int] = {}
        masvs_categories: dict[str, int] = {}
        for finding in findings:
            severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1
            if finding.masvs_category:
                masvs_categories[finding.masvs_category] = (
                    masvs_categories.get(finding.masvs_category, 0) + 1
                )

        return MobileReportSummary(
            application_id=app.id,
            package_name=app.package_name,
            platform=app.platform,
            analysis_status=app.analysis_status,
            security_score=app.security_score,
            findings_count=app.findings_count,
            severity_counts=severity_counts,
            masvs_categories=masvs_categories,
            analyzed_at=app.analyzed_at,
            generated_at=datetime.now(UTC),
        )


def _to_analyzed_finding(app: MobileApplication, item: MobileFinding) -> AnalyzedFinding:
    component = item.affected_component or app.package_name or "android-app"
    analyzed = AnalyzedFinding(
        correlation_key=item.source_rule_id,
        title=item.title,
        description=item.description,
        severity=item.severity,
        affected_url=app.package_name or f"mobile://{app.id}",
        remediation=item.remediation,
        confidence=item.confidence,
        evidence=item.evidence,
        source_tools=["mobile_static"],
        source_rule_ids=[item.source_rule_id],
        verified_confidence=item.confidence,
        verification_status="verified",
        verification_notes="Static APK analysis",
        asset_type="mobile",
        platform="android",
        masvs_category=item.masvs_category,
        affected_component=component,
        exposure_score=1.0,
    )
    analyzed.risk_score = calculate_risk_score(analyzed)
    analyzed.risk_breakdown = build_risk_breakdown(analyzed)  # type: ignore[assignment]
    analyzed.risk_model_version = RISK_MODEL_VERSION  # type: ignore[assignment]
    return analyzed


def _compute_security_score(findings: list) -> float:
    if not findings:
        return 100.0
    penalty = 0.0
    weights = {"critical": 25.0, "high": 15.0, "medium": 8.0, "low": 3.0, "info": 1.0}
    for finding in findings:
        penalty += weights.get(finding.severity, 5.0)
    return round(max(0.0, min(100.0, 100.0 - penalty)), 1)
