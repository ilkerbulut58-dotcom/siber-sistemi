"""Read models for platform-only benchmark quality endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BenchmarkRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    benchmark_target_id: UUID
    scan_id: UUID | None
    mobile_application_id: UUID | None
    git_commit: str | None
    scan_profile: str | None
    fixture_set: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    duration_seconds: float | None
    error_log: str | None


class QualitySummaryResponse(BaseModel):
    precision: float
    recall: float
    f1_score: float
    false_positive_rate: float
    false_negative_rate: float
    average_duration_seconds: float
    expected_count: int = 0
    true_positive_count: int = 0
    false_negative_count: int = 0
    false_positive_count: int = 0
    duplicate_count: int = 0
    scanner_error_count: int = 0
    last_run: BenchmarkRunResponse | None
    by_target_type: dict[str, dict[str, float | int]]
    scanner_health: dict[str, Any]
    baseline_delta: dict[str, Any] | None = None
