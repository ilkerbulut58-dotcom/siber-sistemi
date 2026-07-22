"""Scan dispatch tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.scan_dispatch import dispatch_scan_job


@pytest.mark.asyncio
async def test_dispatch_prefers_background_tasks_over_celery() -> None:
    scan_id = uuid4()
    background_tasks = MagicMock()
    db = AsyncMock()

    await dispatch_scan_job(
        scan_id,
        db=db,
        background_tasks=background_tasks,
    )

    background_tasks.add_task.assert_called_once()
    db.execute.assert_not_awaited()
