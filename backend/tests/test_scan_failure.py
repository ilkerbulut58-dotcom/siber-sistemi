"""Scan failure and Celery timeout handling tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from celery.exceptions import SoftTimeLimitExceeded

from app.models.scan import ScanStatus
from app.services.scan_service import fail_scan_job_by_id, recover_stale_scan_jobs
from app.tasks.scan_tasks import run_scan_job_task


@pytest.mark.asyncio
async def test_fail_scan_job_by_id_marks_active_scan_failed() -> None:
    scan_id = uuid4()
    scan = MagicMock()
    scan.status = ScanStatus.RUNNING
    scan.id = scan_id

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = scan

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    await fail_scan_job_by_id(scan_id, "test error", mock_factory)

    assert scan.status == ScanStatus.FAILED
    assert scan.error_log == "test error"
    assert scan.completed_at is not None
    mock_db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_fail_scan_job_skips_completed() -> None:
    scan_id = uuid4()
    scan = MagicMock()
    scan.status = ScanStatus.COMPLETED

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = scan

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    await fail_scan_job_by_id(scan_id, "ignored", mock_factory)
    mock_db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_recover_stale_uses_started_at() -> None:
    stale_scan = MagicMock()
    stale_scan.status = ScanStatus.RUNNING
    stale_scan.started_at = datetime.now(UTC) - timedelta(minutes=20)
    stale_scan.created_at = datetime.now(UTC) - timedelta(minutes=5)
    stale_scan.id = "scan-stale"

    mock_result = MagicMock()
    mock_result.scalars.return_value = [stale_scan]
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.services.scan_service.get_settings") as mock_settings:
        mock_settings.return_value.scan_stale_minutes = 12
        recovered = await recover_stale_scan_jobs(mock_db)

    assert recovered == 1
    assert stale_scan.status == ScanStatus.FAILED


def test_celery_scan_task_marks_failed_on_soft_timeout() -> None:
    scan_id = str(uuid4())

    with patch("app.tasks.scan_tasks.asyncio.run") as mock_run:
        mock_run.side_effect = [SoftTimeLimitExceeded(), None]
        result = run_scan_job_task.run(scan_id)

    assert result["status"] == "failed"
    assert result["error"] == "timeout"
    assert mock_run.call_count == 2
