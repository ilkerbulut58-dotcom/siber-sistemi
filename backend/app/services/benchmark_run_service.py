"""Persist real scanner outcomes as benchmark measurements."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.benchmark import (
    BenchmarkFindingMatch,
    BenchmarkResult,
    BenchmarkRun,
    BenchmarkRunStatus,
    ExpectedFinding,
)
from app.models.finding import Finding
from app.models.organization import Organization
from app.models.scan import ScanJob
from app.models.mobile_application import MobileApplication
from app.services.benchmark_matching_service import match_findings


class BenchmarkRunService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def complete_for_scan(self, scan: ScanJob) -> None:
        """Evaluate only an explicitly linked run in a hidden system workspace."""
        run = (
            await self.db.execute(select(BenchmarkRun).where(BenchmarkRun.scan_id == scan.id))
        ).scalar_one_or_none()
        if run is None:
            return
        organization = (
            await self.db.execute(select(Organization).where(Organization.id == scan.organization_id))
        ).scalar_one_or_none()
        if organization is None or not organization.is_system_scope:
            return
        existing_result = (
            await self.db.execute(select(BenchmarkResult).where(BenchmarkResult.benchmark_run_id == run.id))
        ).scalar_one_or_none()
        if existing_result is not None:
            return
        expected = list(
            (
                await self.db.execute(
                    select(ExpectedFinding).where(ExpectedFinding.benchmark_target_id == run.benchmark_target_id)
                )
            ).scalars()
        )
        actual = list(
            (await self.db.execute(select(Finding).where(Finding.scan_job_id == scan.id))).scalars()
        )
        records, metrics = match_findings(expected, actual)
        for record in records:
            self.db.add(BenchmarkFindingMatch(
                benchmark_run_id=run.id,
                expected_finding_id=record.expected_id,
                finding_id=record.finding_id,
                classification=record.classification,
                match_reason=record.reason,
            ))
        run.status = BenchmarkRunStatus.COMPLETED
        run.completed_at = datetime.now(UTC)
        if scan.started_at:
            run.duration_seconds = (run.completed_at - scan.started_at).total_seconds()
        self.db.add(BenchmarkResult(
            benchmark_run_id=run.id,
            expected_count=metrics.expected_count,
            true_positive_count=metrics.true_positive_count,
            false_negative_count=metrics.false_negative_count,
            false_positive_count=metrics.false_positive_count,
            duplicate_count=metrics.duplicate_count,
            scanner_error_count=metrics.scanner_error_count,
            precision=metrics.precision,
            recall=metrics.recall,
            f1_score=metrics.f1_score,
            breakdown=metrics.as_dict(),
        ))

    async def complete_for_mobile(self, app: MobileApplication) -> None:
        run = (
            await self.db.execute(
                select(BenchmarkRun).where(BenchmarkRun.mobile_application_id == app.id)
            )
        ).scalar_one_or_none()
        if run is None:
            return
        organization = (
            await self.db.execute(select(Organization).where(Organization.id == app.organization_id))
        ).scalar_one_or_none()
        if organization is None or not organization.is_system_scope:
            return
        existing_result = (
            await self.db.execute(select(BenchmarkResult).where(BenchmarkResult.benchmark_run_id == run.id))
        ).scalar_one_or_none()
        if existing_result is not None:
            return
        expected = list((await self.db.execute(
            select(ExpectedFinding).where(ExpectedFinding.benchmark_target_id == run.benchmark_target_id)
        )).scalars())
        actual = list((await self.db.execute(
            select(Finding).where(Finding.mobile_application_id == app.id)
        )).scalars())
        records, metrics = match_findings(expected, actual)
        for record in records:
            self.db.add(BenchmarkFindingMatch(
                benchmark_run_id=run.id, expected_finding_id=record.expected_id,
                finding_id=record.finding_id, classification=record.classification,
                match_reason=record.reason,
            ))
        run.status = BenchmarkRunStatus.COMPLETED
        run.completed_at = datetime.now(UTC)
        self.db.add(BenchmarkResult(
            benchmark_run_id=run.id, expected_count=metrics.expected_count,
            true_positive_count=metrics.true_positive_count,
            false_negative_count=metrics.false_negative_count,
            false_positive_count=metrics.false_positive_count,
            duplicate_count=metrics.duplicate_count,
            scanner_error_count=metrics.scanner_error_count,
            precision=metrics.precision, recall=metrics.recall, f1_score=metrics.f1_score,
            breakdown=metrics.as_dict(),
        ))
