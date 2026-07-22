"""Continuous monitoring and scheduled scans."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.finding import Finding
from app.models.finding_history import FindingHistory
from app.models.monitoring import MonitoringEvent, MonitoringEventType, ScanSchedule
from app.models.scan import ScanJob
from app.models.user import User
from app.schemas.monitoring import ScanScheduleCreate, ScanScheduleUpdate
from app.schemas.scan import ScanCreate
from app.services.scan_service import ScanService

logger = logging.getLogger(__name__)


class MonitoringService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_schedule(
        self,
        organization_id: UUID,
        data: ScanScheduleCreate,
        *,
        actor: User,
    ) -> ScanSchedule:
        schedule = ScanSchedule(
            organization_id=organization_id,
            project_id=data.project_id,
            domain_id=data.domain_id,
            created_by=actor.id,
            name=data.name,
            target_url=str(data.target_url),
            scan_profile=data.scan_profile,
            interval_hours=data.interval_hours,
            enabled=data.enabled,
            next_run_at=datetime.now(UTC),
        )
        self.db.add(schedule)
        await self.db.flush()
        return schedule

    async def list_schedules(self, organization_id: UUID) -> list[ScanSchedule]:
        result = await self.db.execute(
            select(ScanSchedule)
            .where(ScanSchedule.organization_id == organization_id)
            .order_by(ScanSchedule.created_at.desc())
        )
        return list(result.scalars())

    async def get_schedule(self, organization_id: UUID, schedule_id: UUID) -> ScanSchedule:
        result = await self.db.execute(
            select(ScanSchedule).where(
                ScanSchedule.id == schedule_id,
                ScanSchedule.organization_id == organization_id,
            )
        )
        schedule = result.scalar_one_or_none()
        if schedule is None:
            raise AppError("NOT_FOUND", "Schedule not found.", status_code=404)
        return schedule

    async def update_schedule(
        self,
        organization_id: UUID,
        schedule_id: UUID,
        data: ScanScheduleUpdate,
    ) -> ScanSchedule:
        schedule = await self.get_schedule(organization_id, schedule_id)
        if data.name is not None:
            schedule.name = data.name
        if data.scan_profile is not None:
            schedule.scan_profile = data.scan_profile
        if data.interval_hours is not None:
            schedule.interval_hours = data.interval_hours
        if data.enabled is not None:
            schedule.enabled = data.enabled
        if data.target_url is not None:
            schedule.target_url = str(data.target_url)
        await self.db.flush()
        return schedule

    async def list_events(
        self,
        organization_id: UUID,
        *,
        schedule_id: UUID | None = None,
        limit: int = 50,
    ) -> list[MonitoringEvent]:
        query = select(MonitoringEvent).where(MonitoringEvent.organization_id == organization_id)
        if schedule_id:
            query = query.where(MonitoringEvent.schedule_id == schedule_id)
        query = query.order_by(MonitoringEvent.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars())

    async def due_schedules(self) -> list[ScanSchedule]:
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(ScanSchedule).where(
                ScanSchedule.enabled.is_(True),
                ScanSchedule.next_run_at.is_not(None),
                ScanSchedule.next_run_at <= now,
            )
        )
        return list(result.scalars())

    async def trigger_schedule(self, schedule: ScanSchedule, *, actor_id: UUID | None = None) -> ScanJob:
        from app.models.user import User as UserModel

        user_id = actor_id or schedule.created_by
        user_result = await self.db.execute(select(UserModel).where(UserModel.id == user_id))
        actor = user_result.scalar_one()

        scan = await ScanService(self.db).create(
            schedule.organization_id,
            ScanCreate(
                project_id=schedule.project_id,
                domain_id=schedule.domain_id,
                scan_profile=schedule.scan_profile,
                target_url=schedule.target_url,
                authorization_accepted=True,
                scope_config={
                    "schedule_id": str(schedule.id),
                    "monitoring": True,
                    "previous_scan_job_id": (
                        str(schedule.last_scan_job_id) if schedule.last_scan_job_id else None
                    ),
                },
            ),
            actor=actor,
        )

        schedule.last_run_at = datetime.now(UTC)
        schedule.next_run_at = schedule.last_run_at + timedelta(hours=schedule.interval_hours)
        schedule.last_scan_job_id = scan.id
        await self.db.flush()
        return scan

    async def analyze_scan_delta(
        self,
        *,
        organization_id: UUID,
        project_id: UUID,
        scan_job_id: UUID,
        previous_scan_job_id: UUID | None,
        schedule_id: UUID | None = None,
    ) -> list[MonitoringEvent]:
        if previous_scan_job_id is None:
            return []

        current = await self._findings_by_correlation(organization_id, scan_job_id)
        previous = await self._findings_by_correlation(organization_id, previous_scan_job_id)
        events: list[MonitoringEvent] = []

        for key, finding in current.items():
            if key not in previous:
                events.append(
                    await self._record_event(
                        organization_id=organization_id,
                        project_id=project_id,
                        schedule_id=schedule_id,
                        scan_job_id=scan_job_id,
                        previous_scan_job_id=previous_scan_job_id,
                        event_type=MonitoringEventType.NEW_FINDING,
                        finding=finding,
                        details={"title": finding.title, "severity": finding.severity},
                    )
                )
                continue

            prev = previous[key]
            if finding.severity != prev.severity:
                events.append(
                    await self._record_event(
                        organization_id=organization_id,
                        project_id=project_id,
                        schedule_id=schedule_id,
                        scan_job_id=scan_job_id,
                        previous_scan_job_id=previous_scan_job_id,
                        event_type=MonitoringEventType.SEVERITY_CHANGED,
                        finding=finding,
                        details={
                            "from": prev.severity,
                            "to": finding.severity,
                            "title": finding.title,
                        },
                    )
                )
            if finding.risk_score and prev.risk_score:
                delta = finding.risk_score - prev.risk_score
                if delta >= 10:
                    events.append(
                        await self._record_event(
                            organization_id=organization_id,
                            project_id=project_id,
                            schedule_id=schedule_id,
                            scan_job_id=scan_job_id,
                            previous_scan_job_id=previous_scan_job_id,
                            event_type=MonitoringEventType.RISK_INCREASED,
                            finding=finding,
                            details={"from": prev.risk_score, "to": finding.risk_score},
                        )
                    )
                elif delta <= -10:
                    events.append(
                        await self._record_event(
                            organization_id=organization_id,
                            project_id=project_id,
                            schedule_id=schedule_id,
                            scan_job_id=scan_job_id,
                            previous_scan_job_id=previous_scan_job_id,
                            event_type=MonitoringEventType.RISK_DECREASED,
                            finding=finding,
                            details={"from": prev.risk_score, "to": finding.risk_score},
                        )
                    )

        for key, finding in previous.items():
            if key not in current:
                events.append(
                    await self._record_event(
                        organization_id=organization_id,
                        project_id=project_id,
                        schedule_id=schedule_id,
                        scan_job_id=scan_job_id,
                        previous_scan_job_id=previous_scan_job_id,
                        event_type=MonitoringEventType.RESOLVED_FINDING,
                        finding=finding,
                        details={"title": finding.title},
                    )
                )

        await self.db.flush()
        logger.info(
            "Monitoring delta for scan %s: %s events",
            scan_job_id,
            len(events),
        )
        return events

    async def _findings_by_correlation(
        self,
        organization_id: UUID,
        scan_job_id: UUID,
    ) -> dict[str, Finding]:
        result = await self.db.execute(
            select(Finding)
            .join(FindingHistory, FindingHistory.finding_id == Finding.id)
            .where(
                Finding.organization_id == organization_id,
                FindingHistory.scan_job_id == scan_job_id,
            )
            .distinct()
        )
        findings = list(result.scalars())
        indexed: dict[str, Finding] = {}
        for finding in findings:
            key = finding.correlation_key or finding.fingerprint
            indexed[key] = finding
        return indexed

    async def _record_event(
        self,
        *,
        organization_id: UUID,
        project_id: UUID,
        schedule_id: UUID | None,
        scan_job_id: UUID,
        previous_scan_job_id: UUID | None,
        event_type: str,
        finding: Finding,
        details: dict | None,
    ) -> MonitoringEvent:
        event = MonitoringEvent(
            organization_id=organization_id,
            project_id=project_id,
            schedule_id=schedule_id,
            scan_job_id=scan_job_id,
            previous_scan_job_id=previous_scan_job_id,
            event_type=event_type,
            finding_id=finding.id,
            correlation_key=finding.correlation_key,
            details=details,
        )
        self.db.add(event)
        return event

    @staticmethod
    async def after_scan_completed(db: AsyncSession, scan: ScanJob) -> None:
        scope = scan.scope_config or {}
        schedule_id_raw = scope.get("schedule_id")
        if not schedule_id_raw:
            return

        previous_raw = scope.get("previous_scan_job_id")
        previous_scan_job_id = UUID(str(previous_raw)) if previous_raw else None

        service = MonitoringService(db)
        await service.analyze_scan_delta(
            organization_id=scan.organization_id,
            project_id=scan.project_id,
            scan_job_id=scan.id,
            previous_scan_job_id=previous_scan_job_id,
            schedule_id=UUID(str(schedule_id_raw)),
        )
