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
    verification_method: str | None = None
    active_scan_allowed: bool = False
    admin_approved_at: datetime | None = None
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
    dns_host: str | None = None
    dns_value: str | None = None
    ttl_recommendation_seconds: int | None = None
    well_known_url: str | None = None
    well_known_content: str | None = None
    meta_tag_html: str | None = None
    verification_valid_days: int = 30


class DomainVerifyResponse(BaseModel):
    domain: DomainResponse
    verified: bool
    message: str
    failure_code: str | None = None
