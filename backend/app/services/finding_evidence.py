"""Resolve nested correlated evidence for display and reports."""

from __future__ import annotations

from typing import Any

_TOOL_PRIORITY = (
    "passive_http",
    "tls_check",
    "zap",
    "nuclei",
    "sensitive_data",
    "exposed_paths",
    "secrets",
)


def flatten_finding_evidence(
    evidence: dict[str, Any] | None,
    *,
    source_tool: str | None = None,
    source_rule_id: str | None = None,
) -> dict[str, Any]:
    """Merge top-level fields with tool_evidence buckets (correlation-safe)."""
    if not evidence:
        return {}

    merged: dict[str, Any] = {}
    tool_evidence = evidence.get("tool_evidence")
    if isinstance(tool_evidence, dict):
        order: list[str] = []
        if source_tool and source_tool in tool_evidence:
            order.append(source_tool)
        for rule_tool in _tool_for_rule(source_rule_id):
            if rule_tool in tool_evidence and rule_tool not in order:
                order.append(rule_tool)
        for preferred in _TOOL_PRIORITY:
            if preferred in tool_evidence and preferred not in order:
                order.append(preferred)
        for tool in tool_evidence:
            if tool not in order:
                order.append(tool)
        for tool in order:
            bucket = tool_evidence.get(tool)
            if isinstance(bucket, dict):
                _merge_dict(merged, bucket)

    for key, value in evidence.items():
        if key in {"tool_evidence", "sources", "correlation_key"}:
            continue
        if key not in merged or merged[key] in (None, "", [], {}):
            merged[key] = value

    return merged


def _merge_dict(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if value is None or value == "" or value == {}:
            continue
        if key not in target or target[key] in (None, "", [], {}):
            target[key] = value


def _tool_for_rule(rule_id: str | None) -> tuple[str, ...]:
    if not rule_id:
        return ()
    if rule_id.startswith("cert-"):
        return ("tls_check", "passive_http")
    if rule_id in {"server-disclosure", "x-powered-by-disclosure"}:
        return ("passive_http", "zap")
    if rule_id.startswith("missing-header-"):
        return ("passive_http", "zap", "nuclei")
    return ()
