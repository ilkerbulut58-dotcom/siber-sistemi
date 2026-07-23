"""Log-only notification provider for closed pilot (no outbound email)."""

from __future__ import annotations

import logging
from typing import Any

from app.notifications.base import NotificationProvider

logger = logging.getLogger(__name__)


class NoopNotificationProvider(NotificationProvider):
    def is_configured(self) -> bool:
        return True

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
        logger.info(
            "notification.noop",
            extra={
                "event_type": event_type,
                "recipient_user_id": recipient_user_id,
                "organization_id": organization_id,
                "subject": subject,
                "metadata": metadata or {},
            },
        )
        return True
