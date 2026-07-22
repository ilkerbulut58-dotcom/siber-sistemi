"""Shared model mixins and enums."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class OrganizationRole(enum.StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    SECURITY_ANALYST = "security_analyst"
    DEVELOPER = "developer"
    VIEWER = "viewer"


ROLE_HIERARCHY: dict[OrganizationRole, int] = {
    OrganizationRole.VIEWER: 1,
    OrganizationRole.DEVELOPER: 2,
    OrganizationRole.SECURITY_ANALYST: 3,
    OrganizationRole.ADMIN: 4,
    OrganizationRole.OWNER: 5,
}


def role_at_least(role: OrganizationRole, minimum: OrganizationRole) -> bool:
    return ROLE_HIERARCHY[role] >= ROLE_HIERARCHY[minimum]
