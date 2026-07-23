"""High-level notification events for pilot operations."""

from __future__ import annotations

import logging
from uuid import UUID

from app.notifications.factory import get_notification_provider

logger = logging.getLogger(__name__)


async def notify_scan_completed(
    *,
    user_id: UUID,
    organization_id: UUID,
    scan_id: UUID,
    target: str,
    findings_count: int,
) -> None:
    provider = get_notification_provider()
    if not provider.is_configured():
        return
    await provider.send(
        event_type="scan.completed",
        recipient_user_id=str(user_id),
        organization_id=str(organization_id),
        subject="Scan completed",
        body=f"Scan of {target} completed with {findings_count} findings.",
        metadata={"scan_id": str(scan_id), "findings_count": findings_count},
    )


async def notify_scan_failed(
    *,
    user_id: UUID,
    organization_id: UUID,
    scan_id: UUID,
    target: str,
    error: str,
) -> None:
    provider = get_notification_provider()
    if not provider.is_configured():
        return
    await provider.send(
        event_type="scan.failed",
        recipient_user_id=str(user_id),
        organization_id=str(organization_id),
        subject="Scan failed",
        body=f"Scan of {target} failed.",
        metadata={"scan_id": str(scan_id), "error": error[:500]},
    )


async def notify_quota_exceeded(
    *,
    user_id: UUID,
    organization_id: UUID,
    quota: int,
) -> None:
    provider = get_notification_provider()
    if not provider.is_configured():
        return
    await provider.send(
        event_type="quota.exceeded",
        recipient_user_id=str(user_id),
        organization_id=str(organization_id),
        subject="Scan quota exceeded",
        body=f"Daily scan quota of {quota} has been reached.",
        metadata={"quota": quota},
    )


async def notify_verification_required(
    *,
    user_id: UUID,
    organization_id: UUID,
    domain_hostname: str,
) -> None:
    provider = get_notification_provider()
    if not provider.is_configured():
        return
    await provider.send(
        event_type="verification.required",
        recipient_user_id=str(user_id),
        organization_id=str(organization_id),
        subject="Domain verification required",
        body=f"Verify ownership of {domain_hostname} before scanning.",
        metadata={"domain_hostname": domain_hostname},
    )
