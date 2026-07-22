"""Isolated detection-quality benchmark models."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin


class BenchmarkTargetType(enum.StrEnum):
    WEB = "web"
    API = "api"
    ANDROID = "android"


class BenchmarkRunStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AutomationSupport(enum.StrEnum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    MANUAL_ONLY = "manual_only"
    UNSUPPORTED = "unsupported"


class BenchmarkClassification(enum.StrEnum):
    TRUE_POSITIVE = "true_positive"
    FALSE_NEGATIVE = "false_negative"
    FALSE_POSITIVE = "false_positive"
    DUPLICATE = "duplicate"
    SCANNER_ERROR = "scanner_error"
    CONFIRMED_FALSE_POSITIVE = "confirmed_false_positive"
    VALID_ADDITIONAL_FINDING = "valid_additional_finding"
    GROUND_TRUTH_MISSING = "ground_truth_missing"
    OUT_OF_SCOPE_INFORMATIONAL = "out_of_scope_informational"
    MATCHER_FAILURE = "matcher_failure"
    UNSUPPORTED = "unsupported"


class BenchmarkTarget(Base, TimestampMixin):
    __tablename__ = "benchmark_targets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    target_reference: Mapped[str] = mapped_column(String(1000), nullable=False)
    environment: Mapped[str] = mapped_column(String(50), nullable=False, default="benchmark")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON)


class ExpectedFinding(Base, TimestampMixin):
    __tablename__ = "expected_findings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    benchmark_target_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("benchmark_targets.id"), nullable=False, index=True
    )
    expected_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str | None] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    affected_location: Mapped[str | None] = mapped_column(String(1000))
    description: Mapped[str | None] = mapped_column(Text)
    detection_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    accepted_alternative_keys: Mapped[list[str] | None] = mapped_column(JSON)
    expected_risk_score: Mapped[float | None] = mapped_column(Float)
    expected_ai_review_status: Mapped[str | None] = mapped_column(String(50))
    automation_support: Mapped[str] = mapped_column(
        String(30), nullable=False, default=AutomationSupport.SUPPORTED
    )
    framework_refs: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)


class BenchmarkRun(Base, TimestampMixin):
    __tablename__ = "benchmark_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    benchmark_target_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("benchmark_targets.id"), nullable=False, index=True
    )
    scan_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("scan_jobs.id"), index=True)
    mobile_application_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    app_version: Mapped[str | None] = mapped_column(String(100))
    git_commit: Mapped[str | None] = mapped_column(String(80), index=True)
    scan_profile: Mapped[str | None] = mapped_column(String(50))
    fixture_set: Mapped[str] = mapped_column(String(100), nullable=False, default="smoke")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=BenchmarkRunStatus.QUEUED)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    scanner_versions: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error_log: Mapped[str | None] = mapped_column(Text)


class BenchmarkResult(Base, TimestampMixin):
    __tablename__ = "benchmark_results"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    benchmark_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("benchmark_runs.id"), nullable=False, unique=True, index=True
    )
    expected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    true_positive_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    false_negative_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    false_positive_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scanner_error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    precision: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    recall: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    f1_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    breakdown: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    previous_delta: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class BenchmarkFindingMatch(Base, TimestampMixin):
    __tablename__ = "benchmark_finding_matches"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    benchmark_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("benchmark_runs.id"), nullable=False, index=True
    )
    expected_finding_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("expected_findings.id"), index=True
    )
    finding_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("findings.id"), index=True)
    classification: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    match_reason: Mapped[str | None] = mapped_column(String(255))
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON)
