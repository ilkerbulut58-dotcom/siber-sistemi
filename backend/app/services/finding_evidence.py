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

_SKIP_TOP_LEVEL = frozenset({"tool_evidence", "sources", "correlation_key"})


def flatten_finding_evidence(
    evidence: dict[str, Any] | None,
    *,
    source_tool: str | None = None,
    source_rule_id: str | None = None,
) -> dict[str, Any]:
    """Merge top-level fields with tool_evidence buckets (correlation-safe)."""
    merged, _conflicts = _flatten_with_conflicts(
        evidence, source_tool=source_tool, source_rule_id=source_rule_id
    )
    return merged


def normalize_finding_evidence(
    evidence: dict[str, Any] | None,
    *,
    source_tool: str | None = None,
    source_rule_id: str | None = None,
) -> dict[str, Any]:
    """Client/report record: promoted values plus provenance; no silent overwrite."""
    if not evidence:
        return {}
    merged, conflicts = _flatten_with_conflicts(
        evidence, source_tool=source_tool, source_rule_id=source_rule_id
    )
    out = dict(merged)
    sources = evidence.get("sources")
    if isinstance(sources, list) and sources:
        out["sources"] = sources
    if conflicts:
        out["evidence_conflicts"] = conflicts
    return out


def _flatten_with_conflicts(
    evidence: dict[str, Any] | None,
    *,
    source_tool: str | None,
    source_rule_id: str | None,
) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    if not evidence:
        return {}, {}

    merged: dict[str, Any] = {}
    origins: dict[str, str] = {}
    conflicts: dict[str, list[dict[str, Any]]] = {}
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
                _merge_dict(merged, bucket, origin=str(tool), origins=origins, conflicts=conflicts)

    for key, value in evidence.items():
        if key in _SKIP_TOP_LEVEL:
            continue
        if key not in merged or merged[key] in (None, "", [], {}):
            merged[key] = value
            origins[key] = "stored"
        elif not _values_equivalent(merged[key], value) and value not in (None, "", [], {}):
            conflicts.setdefault(key, []).append(
                {"origin": origins.get(key, "stored"), "value": merged[key]}
            )
            conflicts[key].append({"origin": "stored", "value": value})

    _promote_zap_evidence_string(merged)
    return merged, conflicts


def _merge_dict(
    target: dict[str, Any],
    source: dict[str, Any],
    *,
    origin: str,
    origins: dict[str, str],
    conflicts: dict[str, list[dict[str, Any]]],
) -> None:
    for key, value in source.items():
        if value is None or value == "" or value == {}:
            continue
        if key not in target or target[key] in (None, "", [], {}):
            target[key] = value
            origins[key] = origin
            continue
        if _values_equivalent(target[key], value):
            continue
        bucket = conflicts.setdefault(key, [])
        if not bucket:
            bucket.append({"origin": origins.get(key, origin), "value": target[key]})
        bucket.append({"origin": origin, "value": value})


def _values_equivalent(left: Any, right: Any) -> bool:
    if left == right:
        return True
    if isinstance(left, str) and isinstance(right, str):
        return left.strip() == right.strip()
    return False


def _promote_zap_evidence_string(merged: dict[str, Any]) -> None:
    snippet = merged.get("evidence")
    if not isinstance(snippet, str) or not snippet.strip():
        return
    if merged.get("header_value") in (None, "", [], {}):
        merged["header_value"] = snippet
    header_name = str(merged.get("header_name") or "").lower()
    if "x-powered-by" in header_name and not merged.get("x_powered_by"):
        merged["x_powered_by"] = snippet
    if header_name == "server" and not merged.get("server"):
        merged["server"] = snippet


def _tool_for_rule(rule_id: str | None) -> tuple[str, ...]:
    if not rule_id:
        return ()
    rule = rule_id.lower()
    if rule.startswith("cert-"):
        return ("tls_check", "passive_http")
    if rule in {"server-disclosure", "x-powered-by-disclosure"} or "x-powered-by" in rule:
        return ("passive_http", "zap")
    if rule.startswith("missing-header-"):
        return ("passive_http", "zap", "nuclei")
    if "csp" in rule or rule.startswith("zap-10055"):
        return ("zap", "passive_http")
    if "cache-control" in rule or rule.startswith("zap-10015"):
        return ("zap", "passive_http")
    return ()
