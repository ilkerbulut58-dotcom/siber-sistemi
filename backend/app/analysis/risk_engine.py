"""Unified risk scoring for analyzed findings."""

from __future__ import annotations

from typing import Any, TypedDict

from app.analysis.correlation_rules import SEVERITY_RANK
from app.analysis.types import AnalyzedFinding

RISK_MODEL_VERSION = "1.0.0"


class RiskBreakdownItem(TypedDict):
    key: str
    label: str
    value: str
    weight: float
    description: str


class RiskBreakdown(TypedDict):
    total: float
    items: list[RiskBreakdownItem]
SEVERITY_BASE: dict[str, float] = {
    "critical": 95.0,
    "high": 80.0,
    "medium": 55.0,
    "low": 30.0,
    "info": 10.0,
}

CONFIDENCE_MULTIPLIER: dict[str, float] = {
    "high": 1.0,
    "medium": 0.78,
    "low": 0.55,
}

# Scanner reliability weight (passive / deterministic tools score higher)
SCANNER_RELIABILITY: dict[str, float] = {
    "passive_http": 0.95,
    "tls_check": 0.95,
    "asm_dns": 0.92,
    "asm_passive": 0.90,
    "zap": 0.88,
    "nuclei": 0.82,
    "deep_scan": 0.75,
    "code_scan": 0.72,
}

CVSS_DEFAULTS: dict[str, float] = {
    "missing-header-strict-transport-security": 5.3,
    "missing-header-x-frame-options": 4.3,
    "missing-header-x-content-type-options": 3.1,
    "missing-header-content-security-policy": 5.0,
    "missing-header-referrer-policy": 3.7,
    "cert-invalid": 7.5,
    "cert-expiring-soon": 5.0,
    "no-https": 7.0,
    "exposed-env-file": 9.0,
    "exposed-git-head": 9.8,
}


def calculate_risk_score(finding: AnalyzedFinding) -> float:
    base = SEVERITY_BASE.get(finding.severity, 40.0)
    conf_mult = CONFIDENCE_MULTIPLIER.get(finding.verified_confidence, 0.7)

    tool_weights = [
        SCANNER_RELIABILITY.get(tool, 0.7) for tool in finding.source_tools
    ] or [0.65]
    scanner_rel = sum(tool_weights) / len(tool_weights)
    agreement_bonus = min(12.0, max(0, len(finding.source_tools) - 1) * 4.0)

    cvss_component = 0.0
    if finding.cvss_score:
        cvss_component = finding.cvss_score * 2.5

    score = (base * conf_mult * finding.exposure_score * scanner_rel) + agreement_bonus
    if cvss_component:
        score = score * 0.7 + cvss_component * 0.3

    verification_penalty = 0.0
    if finding.verification_status == "inconclusive":
        verification_penalty = 15.0
    elif finding.verification_status == "unverified":
        verification_penalty = 8.0

    return round(max(1.0, min(100.0, score - verification_penalty)), 1)


def _exposure_score_from_url(url: str | None) -> float:
    if not url:
        return 0.7
    if url.startswith("https://"):
        return 1.0
    if url.startswith("http://"):
        return 0.85
    return 0.7


def build_risk_breakdown(finding: AnalyzedFinding) -> RiskBreakdown:
    """Build explainable risk breakdown — single source of truth for API."""
    tools = list(finding.source_tools) or ["unknown"]
    conf_key = finding.verified_confidence or "medium"
    conf_mult = CONFIDENCE_MULTIPLIER.get(conf_key, 0.7)
    base = SEVERITY_BASE.get(finding.severity, 40.0)
    exposure = finding.exposure_score or _exposure_score_from_url(finding.affected_url)

    tool_weights = [SCANNER_RELIABILITY.get(t, 0.7) for t in tools]
    scanner_rel = sum(tool_weights) / len(tool_weights)
    agreement_bonus = min(12.0, max(0, len(tools) - 1) * 4.0)

    cvss = finding.cvss_score or 0.0
    verification_penalty = 0.0
    if finding.verification_status == "inconclusive":
        verification_penalty = 15.0
    elif finding.verification_status == "unverified":
        verification_penalty = 8.0

    total = finding.risk_score if finding.risk_score is not None else calculate_risk_score(finding)

    items: list[RiskBreakdownItem] = [
        {
            "key": "severity",
            "label": "Önem derecesi",
            "value": f"{base}/100 taban",
            "weight": base / 100.0,
            "description": f"{finding.severity} seviyesi temel risk katkısı sağlar.",
        },
        {
            "key": "confidence",
            "label": "Güven",
            "value": f"{round(conf_mult * 100)}% çarpan",
            "weight": conf_mult,
            "description": "Doğrulama ve kaynak güvenilirliğine göre ayarlanır.",
        },
        {
            "key": "cvss",
            "label": "CVSS",
            "value": f"{cvss:.1f}" if cvss else "—",
            "weight": min(1.0, cvss / 10.0) if cvss else 0.1,
            "description": "Standart CVSS skoru risk hesabına dahil edilir."
            if cvss
            else "CVSS atanmamış.",
        },
        {
            "key": "exposure",
            "label": "Maruziyet",
            "value": f"{round(exposure * 100)}%",
            "weight": exposure,
            "description": "Hedef maruziyet faktörü.",
        },
        {
            "key": "scanner",
            "label": "Tarayıcı güvenilirliği",
            "value": f"{round(scanner_rel * 100)}%",
            "weight": scanner_rel,
            "description": ", ".join(tools),
        },
        {
            "key": "verification",
            "label": "Doğrulama durumu",
            "value": finding.verification_status or "unverified",
            "weight": 0.4 if verification_penalty else 0.85,
            "description": finding.verification_notes
            or ("Pasif doğrulama belirsiz." if verification_penalty else "Doğrulama tamamlandı veya uygulanmadı."),
        },
    ]
    if agreement_bonus > 0:
        items.append(
            {
                "key": "correlation",
                "label": "Çoklu kaynak",
                "value": f"+{agreement_bonus} bonus",
                "weight": agreement_bonus / 12.0,
                "description": f"{len(tools)} farklı tarayıcı aynı bulguyu raporladı.",
            }
        )

    return {"total": total, "items": items}


def score_findings(findings: list[AnalyzedFinding]) -> list[AnalyzedFinding]:
    for finding in findings:
        finding.cvss_score = finding.cvss_score or CVSS_DEFAULTS.get(finding.correlation_key)
        finding.risk_score = calculate_risk_score(finding)
        breakdown: RiskBreakdown = build_risk_breakdown(finding)
        finding.risk_breakdown = breakdown  # type: ignore[attr-defined]
        finding.risk_model_version = RISK_MODEL_VERSION  # type: ignore[attr-defined]
    findings.sort(key=lambda f: (-f.risk_score, -SEVERITY_RANK.get(f.severity, 0)))
    return findings
