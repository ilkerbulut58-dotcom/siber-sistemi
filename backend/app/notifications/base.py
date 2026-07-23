"""Notification provider abstraction for pilot operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class NotificationProvider(ABC):
    @abstractmethod
    def is_configured(self) -> bool:
        """Return True when the provider can deliver notifications."""

    @abstractmethod
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
        """Deliver a notification. Returns True when accepted for delivery."""
