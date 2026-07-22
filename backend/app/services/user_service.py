"""User profile business logic."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import PasswordChangeRequest, UserProfileUpdate
from app.services.audit_service import log_audit_event


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def update_profile(self, user: User, data: UserProfileUpdate) -> User:
        if data.full_name is not None:
            user.full_name = data.full_name
        await self.db.flush()
        return user

    async def change_password(
        self,
        user: User,
        data: PasswordChangeRequest,
        *,
        ip_address: str | None = None,
    ) -> None:
        if not verify_password(data.current_password, user.password_hash):
            raise AppError("INVALID_CREDENTIALS", "Current password is incorrect.", status_code=400)
        user.password_hash = hash_password(data.new_password)
        await log_audit_event(
            self.db,
            action="user.password_changed",
            user_id=user.id,
            resource_type="user",
            resource_id=user.id,
            ip_address=ip_address,
        )
