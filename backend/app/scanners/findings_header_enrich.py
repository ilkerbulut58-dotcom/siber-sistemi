"""Attach observed HTTP header snapshots to findings (new scans only)."""

from __future__ import annotations

from app.scanners.base import RawFinding

_HEADER_KEYS = (
    "content-security-policy",
    "content-security-policy-report-only",
    "cache-control",
    "x-powered-by",
    "server",
)


def enrich_findings_with_observed_headers(
    findings: list[RawFinding],
    headers_lower: dict[str, str] | None,
) -> list[RawFinding]:
    if not headers_lower:
        return findings
    snapshot = {k: headers_lower[k] for k in _HEADER_KEYS if k in headers_lower}
    if not snapshot:
        return findings

    for finding in findings:
        evidence = dict(finding.evidence or {})
        title = (finding.title or "").lower()
        rule = (finding.source_rule_id or "").lower()

        if "csp" in title or "content-security" in title or "csp" in rule:
            if "content-security-policy" in snapshot:
                evidence["evidence_type"] = "http_header"
                evidence["header_name"] = "Content-Security-Policy"
                evidence["header_value"] = snapshot["content-security-policy"][:4000]
            if "content-security-policy-report-only" in snapshot:
                evidence["report_only_policy"] = snapshot["content-security-policy-report-only"][:4000]
        if ("cache" in title or "cache-control" in rule) and "cache-control" in snapshot:
            evidence["evidence_type"] = "http_header"
            evidence["header_name"] = "Cache-Control"
            evidence["header_value"] = snapshot["cache-control"][:2000]
        if ("x-powered-by" in title or "x-powered-by" in rule) and "x-powered-by" in snapshot:
            evidence.setdefault("evidence_type", "http_header")
            evidence["header_name"] = "X-Powered-By"
            evidence["header_value"] = snapshot["x-powered-by"][:500]
        if "server" in title and "disclosure" in title and "server" in snapshot:
            evidence.setdefault("evidence_type", "http_header")
            evidence["header_name"] = "Server"
            evidence["header_value"] = snapshot["server"][:500]

        if evidence != (finding.evidence or {}):
            finding.evidence = evidence
    return findings
