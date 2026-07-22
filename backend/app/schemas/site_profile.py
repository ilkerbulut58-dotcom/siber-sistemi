"""Target site profile schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SensitiveDataSummary(BaseModel):
    password_findings: int = 0
    bank_findings: int = 0
    payment_findings: int = 0
    other_secrets: int = 0
    note: str = (
        "Hassas veri analizi web yanıtlarında yapılır; ASM saldırı yüzeyi keşfi ile karıştırılmamalıdır."
    )


class SiteProfileResponse(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: UUID
    scan_job_id: UUID
    target_url: str
    hostname: str
    profile: dict[str, Any]
    sensitive_data: SensitiveDataSummary
    collected_at: datetime

    model_config = {"from_attributes": True}
