"""In-memory notification capture for pilot simulation tests."""

from __future__ import annotations

from typing import Any

from app.notifications.base import NotificationProvider


class CaptureNotificationProvider(NotificationProvider):
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def is_configured(self) -> bool:
        return True

    def clear(self) -> None:
        self.events.clear()

    async def send(
        self,
        *,
        event_type: str,
        recipient_user_id: str,
        organization_id: str,
        subject: str,
        body: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        self.events.append(
            {
                "event_type": event_type,
                "recipient_user_id": recipient_user_id,
                "organization_id": organization_id,
                "subject": subject,
                "body": body,
                "metadata": metadata or {},
            }
        )
        return True
