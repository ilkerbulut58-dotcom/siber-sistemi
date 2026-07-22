"""Platform-only benchmark quality read model."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.benchmark import BenchmarkResult, BenchmarkRun, BenchmarkTarget
from app.schemas.benchmark import QualitySummaryResponse


class BenchmarkQualityService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def summary(self) -> QualitySummaryResponse:
        result = await self.db.execute(
            select(BenchmarkResult, BenchmarkRun)
            .join(BenchmarkRun, BenchmarkResult.benchmark_run_id == BenchmarkRun.id)
            .order_by(BenchmarkRun.created_at.desc())
        )
        rows = list(result.all())
        last_run = rows[0][1] if rows else None
        latest_result = rows[0][0] if rows else None
        if not rows:
            return QualitySummaryResponse(
                precision=0, recall=0, f1_score=0, false_positive_rate=0,
                false_negative_rate=0, average_duration_seconds=0, last_run=None,
                by_target_type={}, scanner_health={"status": "no_runs"},
            )
        results = [row[0] for row in rows]
        total_tp = sum(item.true_positive_count for item in results)
        total_fp = sum(item.false_positive_count for item in results)
        total_fn = sum(item.false_negative_count for item in results)
        expected = sum(item.expected_count for item in results)
        precision = total_tp / (total_tp + total_fp) if total_tp + total_fp else 0
        recall = total_tp / expected if expected else 0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
        durations = [row[1].duration_seconds for row in rows if row[1].duration_seconds is not None]
        return QualitySummaryResponse(
            precision=precision,
            recall=recall,
            f1_score=f1,
            false_positive_rate=total_fp / (total_tp + total_fp) if total_tp + total_fp else 0,
            false_negative_rate=total_fn / expected if expected else 0,
            average_duration_seconds=sum(durations) / len(durations) if durations else 0,
            expected_count=latest_result.expected_count if latest_result else 0,
            true_positive_count=latest_result.true_positive_count if latest_result else 0,
            false_negative_count=latest_result.false_negative_count if latest_result else 0,
            false_positive_count=latest_result.false_positive_count if latest_result else 0,
            duplicate_count=latest_result.duplicate_count if latest_result else 0,
            scanner_error_count=latest_result.scanner_error_count if latest_result else 0,
            last_run=last_run,
            by_target_type=await self._by_target_type(),
            scanner_health={"failed_runs": sum(1 for _, run in rows if run.status == "failed")},
            baseline_delta=latest_result.previous_delta if latest_result else None,
        )

    async def _by_target_type(self) -> dict[str, dict[str, float | int]]:
        result = await self.db.execute(
            select(BenchmarkTarget.target_type, BenchmarkResult)
            .join(BenchmarkRun, BenchmarkRun.benchmark_target_id == BenchmarkTarget.id)
            .join(BenchmarkResult, BenchmarkResult.benchmark_run_id == BenchmarkRun.id)
        )
        grouped: dict[str, list[BenchmarkResult]] = {}
        for target_type, row in result.all():
            grouped.setdefault(target_type, []).append(row)
        return {
            key: {
                "runs": len(items),
                "precision": sum(item.precision for item in items) / len(items),
                "recall": sum(item.recall for item in items) / len(items),
                "f1_score": sum(item.f1_score for item in items) / len(items),
            }
            for key, items in grouped.items()
        }
