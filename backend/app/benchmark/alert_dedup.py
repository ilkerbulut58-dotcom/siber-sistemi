"""Canonical ZAP alert deduplication for deterministic benchmark and customer views."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from app.scanners.base import RawFinding
from app.utils.url_canonicalization import canonicalize_url

_EVIDENCE_CLASS_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"header", re.I), "header"),
    (re.compile(r"cookie", re.I), "cookie"),
    (re.compile(r"csrf|cross.?site", re.I), "csrf"),
    (re.compile(r"sql|injection", re.I), "injection"),
    (re.compile(r"xss|script", re.I), "xss"),
    (re.compile(r"cors", re.I), "cors"),
    (re.compile(r"redirect", re.I), "redirect"),
    (re.compile(r"disclosure|information", re.I), "disclosure"),
]


def _evidence_class(alert: dict[str, Any]) -> str:
    haystack = " ".join(
        str(alert.get(key) or "")
        for key in ("name", "alert", "description", "attack", "evidence", "param")
    )
    for pattern, label in _EVIDENCE_CLASS_PATTERNS:
        if pattern.search(haystack):
            return label
    return "generic"


def zap_alert_fingerprint(alert: dict[str, Any], *, http_method: str = "GET") -> str:
    """Stable fingerprint for grouping duplicate ZAP alert instances."""
    plugin_id = str(alert.get("pluginId") or alert.get("pluginid") or "unknown")
    normalized_url = canonicalize_url(str(alert.get("url") or alert.get("uri") or ""))
    method = (alert.get("method") or http_method or "GET").upper()
    param = str(alert.get("param") or "").strip().lower()
    attack = str(alert.get("attack") or "").strip().lower()
    evidence_class = _evidence_class(alert)
    vuln_type = str(alert.get("name") or alert.get("alert") or plugin_id).strip().lower()
    payload = "|".join(
        [
            "zap",
            plugin_id,
            normalized_url,
            method,
            param,
            attack,
            evidence_class,
            vuln_type,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class GroupedZapAlert:
    fingerprint: str
    primary_alert: dict[str, Any]
    child_endpoints: list[str] = field(default_factory=list)
    instance_count: int = 1


def group_zap_alerts(alerts: list[dict[str, Any]]) -> list[GroupedZapAlert]:
    """Group alert instances sharing the same canonical fingerprint."""
    buckets: dict[str, GroupedZapAlert] = {}
    for alert in alerts:
        fingerprint = zap_alert_fingerprint(alert)
        url = canonicalize_url(str(alert.get("url") or alert.get("uri") or ""))
        existing = buckets.get(fingerprint)
        if existing is None:
            buckets[fingerprint] = GroupedZapAlert(
                fingerprint=fingerprint,
                primary_alert=alert,
                child_endpoints=[url] if url else [],
                instance_count=1,
            )
            continue
        existing.instance_count += 1
        if url and url not in existing.child_endpoints:
            existing.child_endpoints.append(url)
    return list(buckets.values())


def grouped_alerts_to_raw_findings(
    groups: list[GroupedZapAlert],
    *,
    risk_map: dict[str, str],
) -> list[RawFinding]:
    """Convert grouped ZAP alerts to deduplicated RawFinding rows."""
    findings: list[RawFinding] = []
    for group in groups:
        alert = group.primary_alert
        plugin_id = str(alert.get("pluginId") or alert.get("pluginid") or "unknown")
        name = str(alert.get("name") or alert.get("alert") or plugin_id)
        url = canonicalize_url(str(alert.get("url") or alert.get("uri") or ""))
        risk = risk_map.get(str(alert.get("risk") or "info").lower(), "info")
        child_endpoints = sorted(set(group.child_endpoints))
        evidence: dict[str, Any] = {
            "plugin_id": plugin_id,
            "cwe_id": alert.get("cweid"),
            "wasc_id": alert.get("wascid"),
            "param": alert.get("param"),
            "evidence": alert.get("evidence"),
            "attack": alert.get("attack"),
            "dedup_fingerprint": group.fingerprint,
            "instance_count": group.instance_count,
        }
        if len(child_endpoints) > 1:
            evidence["affected_endpoints"] = child_endpoints
        findings.append(
            RawFinding(
                source_tool="zap",
                source_rule_id=f"zap-{plugin_id}",
                title=name,
                description=str(alert.get("description") or name),
                severity=risk,
                affected_url=url or str(alert.get("uri") or ""),
                remediation=str(alert.get("solution") or "") or None,
                confidence=str(alert.get("confidence") or "medium").lower(),
                evidence=evidence,
            )
        )
    return findings
