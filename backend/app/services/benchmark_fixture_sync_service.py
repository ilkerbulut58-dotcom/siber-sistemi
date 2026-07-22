"""Sync repository ground truth into benchmark tables."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.benchmark.fixtures import BenchmarkFixture
from app.benchmark.manifests import SuiteTargetManifest
from app.models.benchmark import BenchmarkTarget, ExpectedFinding


class BenchmarkFixtureSyncService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def sync_target(
        self,
        suite_target: SuiteTargetManifest,
        ground_truth: BenchmarkFixture,
    ) -> BenchmarkTarget:
        result = await self.db.execute(
            select(BenchmarkTarget).where(BenchmarkTarget.name == suite_target.name)
        )
        target = result.scalar_one_or_none()
        reference = suite_target.target_url or suite_target.artifact_script or ""
        if target is None:
            target = BenchmarkTarget(
                name=suite_target.name,
                target_type=suite_target.target_type,
                target_reference=reference,
                environment=ground_truth.environment,
                enabled=True,
                metadata_={"suite": ground_truth.target},
            )
            self.db.add(target)
            await self.db.flush()
        else:
            target.target_reference = reference
            target.enabled = True

        existing = {
            row.expected_key: row
            for row in (
                await self.db.execute(
                    select(ExpectedFinding).where(ExpectedFinding.benchmark_target_id == target.id)
                )
            ).scalars()
        }
        seen: set[str] = set()
        for item in ground_truth.expected_findings:
            seen.add(item.expected_key)
            row = existing.get(item.expected_key)
            if row is None:
                row = ExpectedFinding(
                    benchmark_target_id=target.id,
                    expected_key=item.expected_key,
                    title=item.title,
                    category=item.category,
                    severity=item.severity,
                    affected_location=item.affected_location,
                    description=item.description,
                    detection_required=item.detection_required,
                    accepted_alternative_keys=item.accepted_alternative_keys,
                )
                self.db.add(row)
            else:
                row.title = item.title
                row.category = item.category
                row.severity = item.severity
                row.affected_location = item.affected_location
                row.description = item.description
                row.detection_required = item.detection_required
                row.accepted_alternative_keys = item.accepted_alternative_keys
        return target
