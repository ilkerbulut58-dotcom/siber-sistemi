"""ASM API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class AsmDiscoverCreate(BaseModel):
    domain_id: UUID
    target_url: HttpUrl
    authorization_accepted: bool = Field(..., description="User confirms authorization to discover")


class AsmDiscoveryJobResponse(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: UUID
    domain_id: UUID
    target_url: str
    status: str
    assets_count: int
    summary: dict[str, Any] | None = None
    error_log: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AssetResponse(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: UUID
    domain_id: UUID
    discovery_job_id: UUID | None = None
    parent_asset_id: UUID | None = None
    asset_type: str
    identifier: str
    url: str | None = None
    status: str
    metadata: dict[str, Any] | None = Field(None, validation_alias="metadata_")
    exposure_score: float
    risk_score: float | None = None
    first_seen_at: datetime
    last_seen_at: datetime
    last_scanned_at: datetime | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}


class AttackSurfaceSummary(BaseModel):
    total_assets: int
    subdomains: int
    ip_addresses: int
    technologies: list[dict[str, str]]
    cdn_waf: list[dict[str, str]]
    dns_records: dict[str, list[str]]
    avg_risk_score: float | None = None
    max_risk_score: float | None = None
    last_discovery_at: datetime | None = None
    last_discovery_status: str | None = None
