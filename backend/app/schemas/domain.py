"""Domain schemas."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class VerificationMethod(StrEnum):
    DNS_TXT = "dns_txt"
    WELL_KNOWN_FILE = "well_known_file"
    META_TAG = "meta_tag"


class DomainCreate(BaseModel):
    hostname: str = Field(min_length=3, max_length=255)
    method: VerificationMethod = VerificationMethod.DNS_TXT


class DomainResponse(BaseModel):
    id: UUID
    project_id: UUID
    organization_id: UUID
    hostname: str
    is_verified: bool
    verified_at: datetime | None
    last_checked_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VerificationInstructions(BaseModel):
    domain_id: UUID
    hostname: str
    method: VerificationMethod
    token: str
    expires_at: datetime
    instructions: list[str]


class DomainVerifyResponse(BaseModel):
    domain: DomainResponse
    verified: bool
    message: str
