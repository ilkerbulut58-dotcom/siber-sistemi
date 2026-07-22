"""Stale scan recovery."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.scan import ScanStatus
from app.services.scan_service import recover_stale_scan_jobs


@pytest.mark.asyncio
async def test_recover_stale_scan_jobs() -> None:
    stale_scan = MagicMock()
    stale_scan.status = ScanStatus.RUNNING
    stale_scan.created_at = datetime.now(UTC) - timedelta(hours=2)
    stale_scan.id = "scan-stale"

    mock_result = MagicMock()
    mock_result.scalars.return_value = [stale_scan]
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.services.scan_service.get_settings") as mock_settings:
        mock_settings.return_value.scan_stale_minutes = 30
        recovered = await recover_stale_scan_jobs(mock_db)

    assert recovered == 1
    assert stale_scan.status == ScanStatus.FAILED
    assert stale_scan.error_log
    assert stale_scan.completed_at is not None
    mock_db.flush.assert_awaited_once()
