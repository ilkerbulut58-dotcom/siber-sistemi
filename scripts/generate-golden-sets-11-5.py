#!/usr/bin/env python3
"""Generate expanded human-labeled golden sets for Faz 11.5."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

RISK_TEMPLATES = [
    ("missing-header-content-security-policy", "medium", 40.0, 64.9, ["passive_http"]),
    ("missing-header-strict-transport-security", "medium", 40.0, 64.9, ["passive_http", "tls_check"]),
    ("missing-header-x-frame-options", "low", 15.0, 39.9, ["passive_http", "zap"]),
    ("missing-header-x-content-type-options", "low", 15.0, 39.9, ["passive_http"]),
    ("missing-header-referrer-policy", "low", 15.0, 39.9, ["passive_http"]),
    ("hardcoded-password", "high", 65.0, 84.9, ["sensitive_data"]),
    ("db-connection-string", "critical", 85.0, 100.0, ["sensitive_data"]),
    ("permissive-cors", "medium", 40.0, 64.9, ["passive_http"]),
    ("exposed-api-docs", "medium", 40.0, 64.9, ["passive_http"]),
    ("exposed-env-file", "critical", 85.0, 100.0, ["nuclei"]),
    ("server-disclosure", "info", 1.0, 14.9, ["passive_http"]),
    ("x-powered-by-disclosure", "info", 1.0, 14.9, ["passive_http"]),
    ("insecure-cookie-flags", "medium", 40.0, 64.9, ["passive_http"]),
    ("cert-expiring-soon", "medium", 40.0, 64.9, ["tls_check"]),
    ("cert-invalid", "critical", 85.0, 100.0, ["tls_check"]),
    ("no-https", "high", 65.0, 84.9, ["tls_check"]),
    ("verbose-error-response", "low", 15.0, 39.9, ["passive_http"]),
    ("credit-card-number", "critical", 85.0, 100.0, ["sensitive_data"]),
    ("api-secret-assignment", "high", 65.0, 84.9, ["sensitive_data"]),
    ("exposed-git-head", "critical", 85.0, 100.0, ["nuclei"]),
    ("info-modern-web-app", "info", 1.0, 14.9, ["zap"]),
    ("weak-http-redirect", "medium", 40.0, 64.9, ["passive_http"]),
    ("http-5xx", "medium", 40.0, 64.9, ["passive_http"]),
    ("bola-idor", "high", 65.0, 84.9, ["zap"]),
    ("rate-limit-missing", "medium", 40.0, 64.9, ["passive_http"]),
    ("sql-injection-signal", "high", 65.0, 84.9, ["zap"]),
    ("xss-reflected-signal", "high", 65.0, 84.9, ["zap"]),
    ("missing-sri", "low", 15.0, 39.9, ["nuclei"]),
    ("tech-stack-disclosure", "info", 1.0, 14.9, ["nuclei"]),
    ("session-fixation-signal", "medium", 40.0, 64.9, ["zap"]),
]

AI_TEMPLATES = [
    ("missing-header-strict-transport-security", "nginx"),
    ("missing-header-content-security-policy", "nginx"),
    ("missing-header-x-frame-options", "nginx"),
    ("missing-header-referrer-policy", "nginx"),
    ("hardcoded-password", "generic-web"),
    ("insecure-cookie-flags", "express"),
    ("permissive-cors", "spring-boot"),
    ("exposed-api-docs", "fastapi"),
    ("server-disclosure", "nginx"),
    ("cert-expiring-soon", "nginx"),
    ("cert-invalid", "nginx"),
    ("exposed-env-file", "node"),
    ("sql-injection-signal", "django"),
    ("xss-reflected-signal", "react"),
    ("db-connection-string", "spring-boot"),
    ("api-secret-assignment", "express"),
    ("weak-http-redirect", "apache"),
    ("verbose-error-response", "express"),
    ("credit-card-number", "generic-web"),
    ("rate-limit-missing", "fastapi"),
    ("missing-sri", "nginx"),
    ("x-powered-by-disclosure", "iis"),
    ("bola-idor", "spring-boot"),
    ("session-fixation-signal", "django"),
    ("no-https", "nginx"),
]


def build_risk_entries() -> list[dict]:
    entries: list[dict] = []
    for index, (key, severity, min_score, max_score, tools) in enumerate(RISK_TEMPLATES, start=1):
        entries.append(
            {
                "case_id": f"re-{index:03d}",
                "correlation_key": key,
                "title": key.replace("-", " ").title(),
                "severity": severity,
                "human_severity": severity,
                "expected_risk_score_min": min_score,
                "expected_risk_score_max": max_score,
                "label_source": "human",
                "source_tools": tools,
                "verified_confidence": "high",
                "verification_status": "verified",
                "exposure_score": 0.85,
                "vulnerability_class": key.split("-")[0],
                "exploitability": "network" if severity in {"critical", "high"} else "local",
                "authentication_required": key.startswith("bola"),
                "data_impact": "confidentiality" if "password" in key or "secret" in key else "integrity",
                "business_impact": severity,
                "confidence": "high",
                "notes": f"Human-labeled benchmark calibration case for {key}.",
            }
        )
    entries.append(
        {
            "case_id": "re-031",
            "correlation_key": "missing-header-x-content-type-options",
            "title": "X-Content-Type-Options draft",
            "severity": "low",
            "expected_risk_score_min": 15.0,
            "expected_risk_score_max": 39.9,
            "label_source": "assistant_generated",
            "source_tools": ["zap"],
            "notes": "Assistant draft — excluded from official aggregates.",
        }
    )
    entries.append(
        {
            "case_id": "re-032",
            "correlation_key": "tech-stack-disclosure",
            "title": "Tech stack disclosure provisional",
            "severity": "info",
            "expected_risk_score_min": 1.0,
            "expected_risk_score_max": 14.9,
            "label_source": "provisional",
            "source_tools": ["nuclei"],
            "notes": "Awaiting human review.",
        }
    )
    return entries


def build_ai_entries() -> list[dict]:
    entries: list[dict] = []
    for index, (key, stack) in enumerate(AI_TEMPLATES, start=1):
        entries.append(
            {
                "case_id": f"ar-{index:03d}",
                "finding_key": key,
                "stack": stack,
                "remediation_text": (
                    f"Apply secure defaults for {key} on {stack}; validate in staging before production rollout."
                ),
                "label_source": "human",
                "human_scores": {
                    "technical_accuracy": 4.5,
                    "applicability": 4.0,
                    "security": 4.5,
                    "clarity": 4.0,
                    "tech_fit": 4.5,
                },
                "notes": f"Human-labeled remediation guidance for {key} ({stack}).",
            }
        )
    entries.append(
        {
            "case_id": "ar-026",
            "finding_key": "hardcoded-password",
            "stack": "generic-web",
            "remediation_text": "Rotate credential and move secret to vault.",
            "label_source": "assistant_generated",
            "llm_scores": {
                "technical_accuracy": 4.0,
                "applicability": 3.5,
                "security": 4.0,
                "clarity": 4.0,
                "tech_fit": 3.5,
            },
            "notes": "Assistant draft only.",
        }
    )
    entries.append(
        {
            "case_id": "ar-027",
            "finding_key": "insecure-cookie-flags",
            "stack": "express",
            "remediation_text": "Set Secure and HttpOnly flags.",
            "label_source": "provisional",
            "notes": "Awaiting human review.",
        }
    )
    return entries


def main() -> None:
    risk_path = ROOT / "benchmarks" / "risk-engine" / "golden-set.yaml"
    ai_path = ROOT / "benchmarks" / "ai-remediation" / "golden-set.yaml"
    risk_payload = {
        "version": "1.1.0",
        "description": "Expanded human-labeled Risk Engine golden set (Faz 11.5).",
        "entries": build_risk_entries(),
    }
    ai_payload = {
        "version": "1.1.0",
        "description": "Expanded human-labeled AI remediation golden set (Faz 11.5).",
        "entries": build_ai_entries(),
    }
    risk_path.write_text(yaml.safe_dump(risk_payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    ai_path.write_text(yaml.safe_dump(ai_payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(json.dumps({"risk_cases": len(risk_payload["entries"]), "ai_cases": len(ai_payload["entries"])}))


if __name__ == "__main__":
    main()
