"""Pytest fixtures for closed pilot simulation."""

from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.notifications.factory import get_notification_provider
from tests.pilot.capture_provider import CaptureNotificationProvider
from tests.pilot.fixtures import PilotWorld, build_pilot_world


@pytest.fixture(autouse=True)
def pilot_simulation_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("BENCHMARK_LAB_ISOLATED", "true")
    monkeypatch.delenv("SKIP_DOMAIN_VERIFICATION", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
    get_notification_provider.cache_clear()


@pytest.fixture
def capture_notifications(monkeypatch: pytest.MonkeyPatch) -> CaptureNotificationProvider:
    provider = CaptureNotificationProvider()
    monkeypatch.setattr(
        "app.notifications.factory.get_notification_provider",
        lambda: provider,
    )
    monkeypatch.setattr(
        "app.notifications.service.get_notification_provider",
        lambda: provider,
    )
    return provider


@pytest.fixture
async def pilot_world(client, db_session) -> PilotWorld:
    return await build_pilot_world(client, db_session)
