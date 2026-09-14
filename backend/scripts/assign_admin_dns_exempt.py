"""Idempotent: grant dns_verification_exempt to verified org admin by email (operator-only).

Usage:
  python -m scripts.assign_admin_dns_exempt ilkerbulut83@hotmail.com
"""

import asyncio
import sys

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.mixins import OrganizationRole
from app.models.organization import OrganizationMember
from app.models.user import User


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: assign_admin_dns_exempt <email>")
        raise SystemExit(1)
    email = sys.argv[1].strip().lower()
    async with async_session_factory() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if user is None:
            print(f"NOT_FOUND: no user with email {email}")
            raise SystemExit(2)
        admin_membership = (
            await session.execute(
                select(OrganizationMember).where(
                    OrganizationMember.user_id == user.id,
                    OrganizationMember.role.in_(
                        [OrganizationRole.ADMIN.value, OrganizationRole.OWNER.value]
                    ),
                )
            )
        ).first()
        if admin_membership is None:
            print(f"NO_ADMIN_ROLE: user {email} is not org admin/owner anywhere")
            raise SystemExit(3)
        if not user.is_email_verified:
            print(f"EMAIL_NOT_VERIFIED: set is_email_verified before granting exempt")
            raise SystemExit(4)
        if user.dns_verification_exempt:
            print(f"OK_ALREADY: {email} already has dns_verification_exempt")
            return
        user.dns_verification_exempt = True
        await session.commit()
        print(f"OK: dns_verification_exempt granted to {email}")


if __name__ == "__main__":
    asyncio.run(main())
