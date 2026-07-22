"""Attack Surface Management shared types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DiscoveredAsset:
    asset_type: str
    identifier: str
    parent_identifier: str | None = None
    status: str = "active"
    metadata: dict[str, Any] = field(default_factory=dict)
    exposure_score: float = 1.0
    url: str | None = None
