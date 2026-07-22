"""Scanner base types."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RawFinding:
    source_tool: str
    source_rule_id: str
    title: str
    description: str
    severity: str
    affected_url: str
    remediation: str | None = None
    confidence: str = "medium"
    evidence: dict[str, Any] = field(default_factory=dict)
    risk_explanation: str | None = None
    remediation_steps: list[str] | None = None
    config_file_paths: list[str] | None = None
    config_snippet: str | None = None
