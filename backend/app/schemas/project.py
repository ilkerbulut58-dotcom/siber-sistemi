"""Project schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    environment: str = Field(default="production", pattern="^(production|staging|development)$")


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    environment: str | None = Field(default=None, pattern="^(production|staging|development)$")


class ProjectResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    environment: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
