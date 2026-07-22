"""Organization schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.mixins import OrganizationRole


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    owner_id: UUID
    is_active: bool
    is_managed_workspace: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrganizationMemberResponse(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    role: OrganizationRole
    invited_by: UUID | None
    joined_at: datetime
    email: str | None = None
    full_name: str | None = None

    model_config = {"from_attributes": True}


class MemberInviteRequest(BaseModel):
    email: str
    role: OrganizationRole = OrganizationRole.VIEWER


class MemberRoleUpdate(BaseModel):
    role: OrganizationRole
