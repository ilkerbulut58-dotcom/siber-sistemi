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
    environment: str
    skip_domain_verification: bool = False


class ReadinessStatus(BaseModel):
    status: str
    version: str
    environment: str
    checks: dict[str, str]
