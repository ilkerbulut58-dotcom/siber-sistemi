"""Correlate multi-scanner findings into single issues."""

from __future__ import annotations

from collections import defaultdict

from app.analysis.correlation_rules import SEVERITY_RANK, normalize_url, resolve_correlation_key
from app.analysis.types import CorrelatedFinding
from app.scanners.base import RawFinding


def correlate_findings(raw_findings: list[RawFinding]) -> list[CorrelatedFinding]:
    groups: dict[tuple[str, str], list[RawFinding]] = defaultdict(list)

    for raw in raw_findings:
        key = resolve_correlation_key(raw.source_tool, raw.source_rule_id, raw.title)
        url = normalize_url(raw.affected_url)
        groups[(key, url)].append(raw)

    correlated: list[CorrelatedFinding] = []
    for (correlation_key, url), items in groups.items():
        correlated.append(_merge_group(correlation_key, url, items))

    correlated.sort(key=lambda f: (-SEVERITY_RANK.get(f.severity, 0), f.correlation_key))
    return correlated


def _merge_group(correlation_key: str, url: str, items: list[RawFinding]) -> CorrelatedFinding:
    items_sorted = sorted(items, key=lambda r: -SEVERITY_RANK.get(r.severity, 0))
    primary = _pick_primary(items_sorted)
    tools = sorted({item.source_tool for item in items})
    rule_ids = sorted({item.source_rule_id for item in items})

    evidence: dict = {
        "correlation_key": correlation_key,
        "source_count": len(items),
        "sources": [
            {
                "tool": item.source_tool,
                "rule_id": item.source_rule_id,
                "severity": item.severity,
            }
            for item in items
        ],
    }
    for item in items:
        if item.evidence:
            evidence.setdefault("tool_evidence", {})[item.source_tool] = item.evidence

    agreement = len(tools)
    if agreement >= 3:
        confidence = "medium"
    elif agreement == 2:
        confidence = "medium"
    else:
        confidence = "low"

    return CorrelatedFinding(
        correlation_key=correlation_key,
        title=primary.title,
        description=primary.description,
        severity=items_sorted[0].severity,
        affected_url=url or primary.affected_url,
        remediation=primary.remediation,
        confidence=confidence,
        evidence=evidence,
        source_tools=tools,
        source_rule_ids=rule_ids,
        raw_sources=items,
        risk_explanation=primary.risk_explanation,
        remediation_steps=primary.remediation_steps,
        config_file_paths=primary.config_file_paths,
        config_snippet=primary.config_snippet,
    )


def _pick_primary(items: list[RawFinding]) -> RawFinding:
    for preferred in ("passive_http", "zap", "nuclei", "code_scan", "deep_scan", "tls_check"):
        for item in items:
            if item.source_tool == preferred:
                return item
    return items[0]
