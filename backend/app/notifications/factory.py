"""Notification provider factory."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.notifications.base import NotificationProvider
from app.notifications.noop_provider import NoopNotificationProvider


@lru_cache
def get_notification_provider() -> NotificationProvider:
    settings = get_settings()
    if settings.notifications_provider == "noop":
        return NoopNotificationProvider()
    raise RuntimeError(
        f"Notification provider {settings.notifications_provider!r} is not implemented. "
        "Use NOTIFICATIONS_PROVIDER=noop for closed pilot."
    )
