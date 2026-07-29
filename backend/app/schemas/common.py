"""Common API response schemas."""

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[Any] = Field(default_factory=list)


class ResponseMeta(BaseModel):
    request_id: str = ""


class PaginatedMeta(ResponseMeta):
    page: int = 1
    page_size: int = 20
    total: int = 0
    total_pages: int = 0


class APIResponse[T](BaseModel):
    success: bool = True
    data: T | None = None
    error: ErrorDetail | None = None
    meta: ResponseMeta = Field(default_factory=ResponseMeta)


class HealthStatus(BaseModel):
    status: str
    version: str
    git_commit: str = ""
    environment: str = ""


class SystemInfo(BaseModel):
    product: str = "SIBER Security Analysis Platform"
    environment: str
    version: str
    git_commit: str
    release_tag: str
    domain_verification_required: bool
    scan_daily_quota: int
    scan_concurrency_limit: int
    allowed_profiles: list[str]
    full_active_enabled: bool = False
    scan_notifications: str
    public_registration_enabled: bool
    support_contact_email: str = ""


class ReadinessStatus(BaseModel):
    status: str
    version: str
    environment: str
    checks: dict[str, str]
