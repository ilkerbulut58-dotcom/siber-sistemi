"""Finding persistence and queries."""

import hashlib
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.finding import Finding, FindingStatus
from app.models.finding_history import FindingHistory
from app.models.scan import ScanJob
from app.models.user import User
from app.analysis.correlation_rules import normalize_url
from app.analysis.pipeline import analyze_scan_findings
from app.analysis.types import AnalyzedFinding
from app.scanners.base import RawFinding
from app.schemas.finding import FindingUpdate
from app.schemas.scan import ScanCreate
from app.security.evidence_sanitizer import sanitize_evidence_dict
from app.services.ai_analysis_service import enrich_finding
from app.services.audit_service import log_audit_event


def build_fingerprint(project_id: UUID, correlation_key: str, affected_url: str) -> str:
    payload = f"{project_id}:{correlation_key}:{normalize_url(affected_url)}"
    return hashlib.sha256(payload.encode()).hexdigest()


def build_mobile_fingerprint(
    project_id: UUID, correlation_key: str, affected_component: str
) -> str:
    payload = f"{project_id}:mobile:{correlation_key}:{affected_component}"
    return hashlib.sha256(payload.encode()).hexdigest()


def build_legacy_fingerprint(project_id: UUID, raw: RawFinding) -> str:
    payload = f"{project_id}:{raw.source_tool}:{raw.source_rule_id}:{raw.affected_url}:{raw.title}"
    return hashlib.sha256(payload.encode()).hexdigest()


class FindingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _log_history(
        self,
        finding_id: UUID,
        event_type: str,
        *,
        scan_job_id: UUID | None = None,
        details: dict | None = None,
    ) -> None:
        self.db.add(
            FindingHistory(
                finding_id=finding_id,
                scan_job_id=scan_job_id,
                event_type=event_type,
                details=details,
            )
        )

    async def persist_scan_findings(
        self,
        *,
        organization_id: UUID,
        project_id: UUID,
        scan_job_id: UUID,
        raw_findings: list[RawFinding],
        target_url: str,
        asset_id: UUID | None = None,
    ) -> list[Finding]:
        analyzed = await analyze_scan_findings(target_url, raw_findings)
        return await self.persist_analyzed_findings(
            organization_id=organization_id,
            project_id=project_id,
            scan_job_id=scan_job_id,
            analyzed_findings=analyzed,
            asset_id=asset_id,
        )

    async def persist_analyzed_findings(
        self,
        *,
        organization_id: UUID,
        project_id: UUID,
        scan_job_id: UUID,
        analyzed_findings: list[AnalyzedFinding],
        asset_id: UUID | None = None,
    ) -> list[Finding]:
        now = datetime.now(UTC)
        saved: list[Finding] = []

        for item in analyzed_findings:
            fingerprint = build_fingerprint(project_id, item.correlation_key, item.affected_url)
            result = await self.db.execute(
                select(Finding).where(
                    Finding.project_id == project_id,
                    Finding.fingerprint == fingerprint,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.last_seen_at = now
                existing.scan_job_id = scan_job_id
                existing.severity = item.severity
                existing.confidence = item.verified_confidence
                existing.correlation_key = item.correlation_key
                existing.risk_score = item.risk_score
                existing.cvss_score = item.cvss_score
                existing.source_tools = item.source_tools
                existing.verification_status = item.verification_status
                existing.verification_notes = item.verification_notes
                existing.evidence = sanitize_evidence_dict(item.evidence)
                existing.risk_breakdown = getattr(item, "risk_breakdown", None)
                existing.risk_model_version = getattr(item, "risk_model_version", None)
                if asset_id:
                    existing.asset_id = asset_id
                existing.source_tool = item.source_tools[0] if item.source_tools else existing.source_tool
                existing.source_rule_id = item.correlation_key
                if item.remediation_steps:
                    existing.title = item.title
                    existing.description = item.description
                    existing.remediation = item.remediation
                    existing.risk_explanation = item.risk_explanation
                    existing.remediation_steps = item.remediation_steps
                    existing.config_file_paths = item.config_file_paths
                    existing.config_snippet = item.config_snippet
                if existing.status == FindingStatus.RESOLVED:
                    existing.status = FindingStatus.OPEN
                    await self._log_history(
                        existing.id,
                        "reopened",
                        scan_job_id=scan_job_id,
                        details={"reason": "detected_again"},
                    )
                else:
                    await self._log_history(
                        existing.id,
                        "redetected",
                        scan_job_id=scan_job_id,
                        details={"risk_score": item.risk_score},
                    )
                enrich_finding(existing)
                saved.append(existing)
                continue

            finding = Finding(
                organization_id=organization_id,
                project_id=project_id,
                scan_job_id=scan_job_id,
                source_tool=item.source_tools[0] if item.source_tools else "correlated",
                source_rule_id=item.correlation_key,
                title=item.title,
                description=item.description,
                affected_url=item.affected_url,
                severity=item.severity,
                confidence=item.verified_confidence,
                correlation_key=item.correlation_key,
                risk_score=item.risk_score,
                cvss_score=item.cvss_score,
                source_tools=item.source_tools,
                verification_status=item.verification_status,
                verification_notes=item.verification_notes,
                evidence=sanitize_evidence_dict(item.evidence or None),
                fingerprint=fingerprint,
                risk_breakdown=getattr(item, "risk_breakdown", None),
                risk_model_version=getattr(item, "risk_model_version", None),
                asset_type=getattr(item, "asset_type", "web"),
                platform=getattr(item, "platform", None),
                masvs_category=getattr(item, "masvs_category", None),
                affected_component=getattr(item, "affected_component", None),
                remediation=item.remediation,
                risk_explanation=item.risk_explanation,
                remediation_steps=item.remediation_steps,
                config_file_paths=item.config_file_paths,
                config_snippet=item.config_snippet,
                asset_id=asset_id,
                first_seen_at=now,
                last_seen_at=now,
            )
            enrich_finding(finding)
            self.db.add(finding)
            await self.db.flush()
            await self._log_history(
                finding.id,
                "detected",
                scan_job_id=scan_job_id,
                details={"risk_score": item.risk_score, "sources": item.source_tools},
            )
            saved.append(finding)

        await self.db.flush()
        return saved

    async def persist_mobile_findings(
        self,
        *,
        organization_id: UUID,
        project_id: UUID,
        mobile_application_id: UUID,
        analyzed_findings: list[AnalyzedFinding],
    ) -> list[Finding]:
        now = datetime.now(UTC)
        saved: list[Finding] = []

        for item in analyzed_findings:
            component = item.affected_component or item.correlation_key
            fingerprint = build_mobile_fingerprint(project_id, item.correlation_key, component)
            result = await self.db.execute(
                select(Finding).where(
                    Finding.project_id == project_id,
                    Finding.fingerprint == fingerprint,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.last_seen_at = now
                existing.mobile_application_id = mobile_application_id
                existing.severity = item.severity
                existing.confidence = item.verified_confidence
                existing.correlation_key = item.correlation_key
                existing.risk_score = item.risk_score
                existing.cvss_score = item.cvss_score
                existing.source_tools = item.source_tools
                existing.verification_status = item.verification_status
                existing.verification_notes = item.verification_notes
                existing.evidence = sanitize_evidence_dict(item.evidence)
                existing.risk_breakdown = getattr(item, "risk_breakdown", None)
                existing.risk_model_version = getattr(item, "risk_model_version", None)
                existing.asset_type = "mobile"
                existing.platform = item.platform or "android"
                existing.masvs_category = item.masvs_category
                existing.affected_component = item.affected_component
                existing.source_tool = item.source_tools[0] if item.source_tools else "mobile_static"
                existing.source_rule_id = item.correlation_key
                if item.remediation:
                    existing.title = item.title
                    existing.description = item.description
                    existing.remediation = item.remediation
                if existing.status == FindingStatus.RESOLVED:
                    existing.status = FindingStatus.OPEN
                    await self._log_history(
                        existing.id,
                        "reopened",
                        details={"reason": "detected_again", "mobile_application_id": str(mobile_application_id)},
                    )
                else:
                    await self._log_history(
                        existing.id,
                        "redetected",
                        details={"risk_score": item.risk_score, "mobile_application_id": str(mobile_application_id)},
                    )
                enrich_finding(existing)
                saved.append(existing)
                continue

            finding = Finding(
                organization_id=organization_id,
                project_id=project_id,
                scan_job_id=None,
                mobile_application_id=mobile_application_id,
                source_tool=item.source_tools[0] if item.source_tools else "mobile_static",
                source_rule_id=item.correlation_key,
                title=item.title,
                description=item.description,
                affected_url=item.affected_url,
                severity=item.severity,
                confidence=item.verified_confidence,
                correlation_key=item.correlation_key,
                risk_score=item.risk_score,
                cvss_score=item.cvss_score,
                source_tools=item.source_tools,
                verification_status=item.verification_status,
                verification_notes=item.verification_notes,
                evidence=sanitize_evidence_dict(item.evidence or None),
                fingerprint=fingerprint,
                risk_breakdown=getattr(item, "risk_breakdown", None),
                risk_model_version=getattr(item, "risk_model_version", None),
                asset_type="mobile",
                platform=item.platform or "android",
                masvs_category=item.masvs_category,
                affected_component=item.affected_component,
                remediation=item.remediation,
                risk_explanation=item.risk_explanation,
                remediation_steps=item.remediation_steps,
                config_file_paths=item.config_file_paths,
                config_snippet=item.config_snippet,
                first_seen_at=now,
                last_seen_at=now,
            )
            enrich_finding(finding)
            self.db.add(finding)
            await self.db.flush()
            await self._log_history(
                finding.id,
                "detected",
                details={
                    "risk_score": item.risk_score,
                    "sources": item.source_tools,
                    "mobile_application_id": str(mobile_application_id),
                },
            )
            saved.append(finding)

        await self.db.flush()
        return saved

    async def list_history(self, organization_id: UUID, finding_id: UUID) -> list[FindingHistory]:
        await self.get(organization_id, finding_id)
        result = await self.db.execute(
            select(FindingHistory)
            .where(FindingHistory.finding_id == finding_id)
            .order_by(FindingHistory.created_at.desc())
        )
        return list(result.scalars())

    async def list_for_scan(self, organization_id: UUID, scan_id: UUID) -> list[Finding]:
        result = await self.db.execute(
            select(Finding)
            .where(
                Finding.organization_id == organization_id,
                Finding.scan_job_id == scan_id,
            )
            .order_by(Finding.created_at.desc())
        )
        return list(result.scalars())

    async def list_for_org(
        self,
        organization_id: UUID,
        *,
        project_id: UUID | None = None,
        scan_id: UUID | None = None,
        severity: str | None = None,
        asset_type: str | None = None,
        mobile_application_id: UUID | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[Finding]:
        query = select(Finding).where(Finding.organization_id == organization_id)
        if project_id:
            query = query.where(Finding.project_id == project_id)
        if scan_id:
            query = query.where(Finding.scan_job_id == scan_id)
        if severity:
            query = query.where(Finding.severity == severity)
        if asset_type:
            query = query.where(Finding.asset_type == asset_type)
        if mobile_application_id:
            query = query.where(Finding.mobile_application_id == mobile_application_id)
        query = query.order_by(Finding.last_seen_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars())

    async def get(self, organization_id: UUID, finding_id: UUID) -> Finding:
        result = await self.db.execute(
            select(Finding).where(
                Finding.id == finding_id,
                Finding.organization_id == organization_id,
            )
        )
        finding = result.scalar_one_or_none()
        if finding is None:
            raise AppError("NOT_FOUND", "Finding not found.", status_code=404)
        return finding

    async def update(
        self,
        finding: Finding,
        data: FindingUpdate,
        *,
        actor: User | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Finding:
        if data.status is not None and data.status != finding.status:
            old = finding.status
            finding.status = data.status
            await self._log_history(
                finding.id,
                "status_change",
                details={"from": old, "to": data.status},
            )
            if actor is not None:
                action = "finding.status_changed"
                if data.status == FindingStatus.ACCEPTED_RISK:
                    action = "finding.risk_accepted"
                await log_audit_event(
                    self.db,
                    action=action,
                    user_id=actor.id,
                    organization_id=finding.organization_id,
                    resource_type="finding",
                    resource_id=finding.id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={
                        "finding_id": str(finding.id),
                        "previous_status": old,
                        "new_status": data.status,
                        "note": data.reviewer_notes,
                    },
                )
        if data.reviewer_notes is not None:
            finding.reviewer_notes = data.reviewer_notes
        await self.db.flush()
        return finding

    async def retest(
        self,
        organization_id: UUID,
        finding_id: UUID,
        *,
        actor: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> ScanJob:
        from app.services.scan_service import ScanService

        finding = await self.get(organization_id, finding_id)
        scan_result = await self.db.execute(
            select(ScanJob).where(ScanJob.id == finding.scan_job_id)
        )
        original = scan_result.scalar_one_or_none()
        if original is None:
            raise AppError("NOT_FOUND", "Original scan not found.", status_code=404)

        scan_service = ScanService(self.db)
        new_scan = await scan_service.create(
            organization_id,
            ScanCreate(
                project_id=finding.project_id,
                domain_id=original.domain_id,
                scan_profile=original.scan_profile,
                target_url=finding.affected_url or original.target_url,
                authorization_accepted=True,
            ),
            actor=actor,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._log_history(
            finding.id,
            "retest_started",
            scan_job_id=new_scan.id,
        )
        await log_audit_event(
            self.db,
            action="finding.retest_started",
            user_id=actor.id,
            organization_id=finding.organization_id,
            resource_type="finding",
            resource_id=finding.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"finding_id": str(finding.id), "scan_id": str(new_scan.id)},
        )
        return new_scan
