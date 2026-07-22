"""Finding schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RiskBreakdownItemResponse(BaseModel):
    key: str
    label: str
    value: str
    weight: float
    description: str


class RiskBreakdownResponse(BaseModel):
    total: float
    items: list[RiskBreakdownItemResponse]


class FindingResponse(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: UUID
    scan_job_id: UUID | None
    source_tool: str
    source_rule_id: str | None
    title: str
    description: str | None
    affected_url: str | None
    severity: str
    confidence: str | None
    correlation_key: str | None = None
    risk_score: float | None = None
    cvss_score: float | None = None
    source_tools: list[str] | None = None
    verification_status: str | None = None
    verification_notes: str | None = None
    evidence: dict | None
    status: str
    remediation: str | None
    risk_explanation: str | None = None
    remediation_steps: list[str] | None = None
    config_file_paths: list[str] | None = None
    config_snippet: str | None = None
    reviewer_notes: str | None = None
    ai_summary: str | None = None
    ai_remediation: str | None = None
    ai_confidence_label: str | None = None
    risk_breakdown: RiskBreakdownResponse | None = None
    risk_model_version: str | None = None
    asset_type: str = "web"
    platform: str | None = None
    masvs_category: str | None = None
    affected_component: str | None = None
    mobile_application_id: UUID | None = None
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime


class FindingUpdate(BaseModel):
    status: str | None = Field(default=None)
    reviewer_notes: str | None = Field(default=None, max_length=5000)


class FindingHistoryResponse(BaseModel):
    id: UUID
    finding_id: UUID
    scan_job_id: UUID | None
    event_type: str
    details: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}
