"""ASM asset risk scoring — integrates with Risk Engine exposure model."""

from __future__ import annotations

from typing import Any


def compute_asset_risk_score(
    metadata: dict[str, Any] | None,
    *,
    exposure_score: float = 1.0,
    max_finding_risk: float | None = None,
    findings_count: int = 0,
) -> float:
    """Compute 1–100 risk score for an asset from surface metadata + linked findings."""
    meta = metadata or {}
    score = 15.0 * exposure_score

    tls = meta.get("tls") or {}
    if tls.get("valid") is False or tls.get("error"):
        score += 25.0
    days = tls.get("days_until_expiry")
    if isinstance(days, int) and days < 30:
        score += 15.0

    http = meta.get("http") or {}
    sec_headers = http.get("security_headers") or {}
    if isinstance(sec_headers, dict):
        missing = sum(1 for v in sec_headers.values() if not v)
        score += missing * 4.0

    technologies = meta.get("technologies") or []
    if isinstance(technologies, list) and len(technologies) > 5:
        score += 5.0

    cdn_waf = meta.get("cdn_waf") or []
    if isinstance(cdn_waf, list) and cdn_waf:
        score -= 3.0

    if max_finding_risk:
        score = score * 0.55 + max_finding_risk * 0.45

    score += min(10.0, findings_count * 2.0)

    return round(max(1.0, min(100.0, score)), 1)
