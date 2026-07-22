"""Quick scan — one-step scan from target URL."""

from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.scan import ScanResponse


class QuickScanCreate(BaseModel):
    target_url: HttpUrl
    scan_profile: str = Field(default="safe")
    authorization_accepted: bool = Field(
        description="User confirms authorization to scan this target."
    )


class QuickScanResponse(BaseModel):
    organization_id: UUID
    project_id: UUID
    domain_id: UUID
    scan: ScanResponse
