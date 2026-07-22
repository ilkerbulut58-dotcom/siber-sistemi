"""Create the initial platform administrator from explicit environment variables."""

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.security import hash_password
from app.models.user import User

async def main() -> None:
    admin_email = os.environ.get("INITIAL_PLATFORM_ADMIN_EMAIL", "").strip().lower()
    admin_password = os.environ.get("INITIAL_PLATFORM_ADMIN_PASSWORD", "")
    if not admin_email or not admin_password:
        print(
            "Skipping platform-admin bootstrap: "
            "INITIAL_PLATFORM_ADMIN_EMAIL and INITIAL_PLATFORM_ADMIN_PASSWORD are required."
        )
        return

    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.email == admin_email))
        user = result.scalar_one_or_none()
        if user:
            user.password_hash = hash_password(admin_password)
            user.is_email_verified = True
            user.is_platform_admin = True
            user.is_active = True
            user.failed_login_count = 0
            user.locked_until = None
            print(f"Updated platform admin user: {admin_email}")
        else:
            db.add(
                User(
                    email=admin_email,
                    password_hash=hash_password(admin_password),
                    full_name="Platform Administrator",
                    is_email_verified=True,
                    is_platform_admin=True,
                    is_active=True,
                )
            )
            print(f"Created platform admin user: {admin_email}")
        await db.commit()


if __name__ == "__main__":
    asyncio.run(main())
