"""Map scanner rule IDs to canonical correlation keys."""

from __future__ import annotations

import re

from app.utils.url_canonicalization import (
    normalize_url,  # noqa: F401 — re-exported for analysis modules
)

# ZAP passive plugin IDs -> canonical keys (aligned with passive_http rule IDs)
ZAP_ALERT_TITLE_MAP: list[tuple[str, str]] = [
    ("server leaks version information", "server-disclosure"),
    ("server leaks information via \"x-powered-by\"", "x-powered-by-disclosure"),
    ("content security policy", "missing-header-content-security-policy"),
    ("strict-transport-security", "missing-header-strict-transport-security"),
    ("x-content-type-options", "missing-header-x-content-type-options"),
    ("x-frame-options", "missing-header-x-frame-options"),
    ("referrer-policy", "missing-header-referrer-policy"),
    ("cross-origin resource sharing", "permissive-cors"),
    ("cross-domain javascript", "cross-domain-javascript-inclusion"),
    ("modern web application", "info-modern-web-app"),
]

ZAP_RULE_MAP: dict[str, str] = {
    "10020": "missing-header-x-frame-options",
    "10021": "missing-header-x-content-type-options",
    "10035": "missing-header-strict-transport-security",
    "10038": "missing-header-content-security-policy",
    "10063": "missing-header-referrer-policy",
    "10096": "server-disclosure",
    "10037": "x-powered-by-disclosure",
    "10098": "permissive-cors",
    "10109": "info-modern-web-app",
}

# Nuclei template id fragments -> canonical keys
NUCLEI_FRAGMENT_MAP: list[tuple[str, str]] = [
    ("strict-transport-security", "missing-header-strict-transport-security"),
    ("x-frame-options", "missing-header-x-frame-options"),
    ("x-content-type-options", "missing-header-x-content-type-options"),
    ("content-security-policy", "missing-header-content-security-policy"),
    ("referrer-policy", "missing-header-referrer-policy"),
    ("x-powered-by", "x-powered-by-disclosure"),
    ("cors", "permissive-cors"),
    ("openapi", "exposed-api-docs"),
    ("swagger", "exposed-api-docs"),
    ("tls", "cert-invalid"),
    ("ssl", "cert-invalid"),
    ("exposure", "exposed-env-file"),
]

SEVERITY_RANK = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}

# sensitive_data scanner rule IDs -> canonical keys
SENSITIVE_DATA_RULE_MAP: dict[str, str] = {
    "sensitive-hardcoded-password": "hardcoded-password",
    "sensitive-db-connection-string": "db-connection-string",
    "sensitive-turkish-iban": "turkish-iban",
    "sensitive-generic-iban": "generic-iban",
    "sensitive-credit-card-number": "credit-card-number",
    "sensitive-bank-account-hint": "bank-account-hint",
    "sensitive-api-secret-assignment": "api-secret-assignment",
}

# Findings that represent the same secret across URLs should deduplicate by secret identity.
SECRET_CORRELATION_KEYS = frozenset(SENSITIVE_DATA_RULE_MAP.values())


def resolve_correlation_key(source_tool: str, source_rule_id: str, title: str) -> str:
    rule = source_rule_id.lower().strip()

    if rule.startswith("zap-"):
        plugin = rule.removeprefix("zap-")
        if plugin in ZAP_RULE_MAP:
            return ZAP_RULE_MAP[plugin]

    if source_tool == "zap":
        title_lower = title.lower()
        for fragment, key in ZAP_ALERT_TITLE_MAP:
            if fragment in title_lower:
                return key

    if source_tool == "passive_http" and rule:
        return rule

    if source_tool == "nuclei":
        rule_lower = rule.lower()
        for fragment, key in NUCLEI_FRAGMENT_MAP:
            if fragment in rule_lower:
                return key

    if source_tool == "code_scan" and rule:
        return rule

    if source_tool == "deep_scan" and rule:
        return f"deep.{rule}"

    if source_tool == "tls_check" and rule:
        return rule

    if source_tool == "sensitive_data" and rule:
        if rule in SENSITIVE_DATA_RULE_MAP:
            return SENSITIVE_DATA_RULE_MAP[rule]
        if rule.startswith("sensitive-"):
            return rule.removeprefix("sensitive-")

    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:80]
    return f"generic.{slug or rule or 'unknown'}"


def secret_identity_token(correlation_key: str, evidence: dict | None) -> str | None:
    """Stable token for deduplicating the same secret observed on multiple URLs."""
    if correlation_key not in SECRET_CORRELATION_KEYS:
        return None
    if not evidence:
        return None
    pattern = str(evidence.get("pattern") or correlation_key)
    masked = str(evidence.get("masked_sample") or "").strip()
    if not masked:
        return None
    return f"{pattern}:{masked}"
