"""Tests for stale ASM discovery job recovery."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.scan import ScanStatus
from app.services.asm_service import recover_stale_asm_jobs


@pytest.mark.asyncio
async def test_recover_stale_asm_jobs() -> None:
    stale_job = MagicMock()
    stale_job.id = uuid4()
    stale_job.status = ScanStatus.QUEUED
    stale_job.started_at = None
    stale_job.created_at = datetime.now(UTC) - timedelta(hours=1)

    mock_result = MagicMock()
    mock_result.scalars.return_value = [stale_job]
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.services.asm_service.get_settings") as mock_settings:
        mock_settings.return_value.scan_stale_minutes = 30
        recovered = await recover_stale_asm_jobs(mock_db)

    assert recovered == 1
    assert stale_job.status == ScanStatus.FAILED
    assert stale_job.completed_at is not None
    assert "30 dakikadan" in stale_job.error_log
