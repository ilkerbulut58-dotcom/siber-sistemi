"""Idempotently grant platform-admin privileges to an existing verified org admin.

Operator-only usage:
  python -m scripts.grant_platform_admin user@example.com
"""

import asyncio
import sys

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.mixins import OrganizationRole
from app.models.organization import OrganizationMember
from app.models.user import User


async def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: grant_platform_admin <email>")
        raise SystemExit(1)

    email = sys.argv[1].strip().lower()
    async with async_session_factory() as session:
        user = (
            await session.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if user is None:
            print(f"NOT_FOUND: no user with email {email}")
            raise SystemExit(2)
        if not user.is_email_verified:
            print(f"EMAIL_NOT_VERIFIED: refusing to promote {email}")
            raise SystemExit(3)

        admin_membership = (
            await session.execute(
                select(OrganizationMember.id)
                .where(
                    OrganizationMember.user_id == user.id,
                    OrganizationMember.role.in_(
                        [OrganizationRole.ADMIN.value, OrganizationRole.OWNER.value]
                    ),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if admin_membership is None:
            print(f"NO_ADMIN_ROLE: {email} is not an organization admin/owner")
            raise SystemExit(4)

        if user.is_platform_admin:
            print(f"OK_ALREADY: {email} is already a platform admin")
            return

        user.is_platform_admin = True
        await session.commit()
        print(f"OK: platform-admin privileges granted to {email}")


if __name__ == "__main__":
    asyncio.run(main())
