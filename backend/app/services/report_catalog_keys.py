"""Map stored finding titles/rule ids to catalog keys without rewriting DB rows."""

from __future__ import annotations

from app.models.finding import Finding


def report_catalog_key(finding: Finding) -> str:
    title = (finding.title or "").lower()
    rule = (finding.source_rule_id or finding.correlation_key or "").strip()
    rule_l = rule.lower()
    plugin = rule_l.removeprefix("zap-") if rule_l.startswith("zap-") else ""

    if "wildcard directive" in title or rule_l.endswith("csp-wildcard-directive"):
        return "generic.csp-wildcard-directive"
    if "script-src" in title and "unsafe-inline" in title:
        return "generic.csp-script-src-unsafe-inline"
    if "style-src" in title and "unsafe-inline" in title:
        return "generic.csp-style-src-unsafe-inline"
    if "cache-control" in title or "re-examine cache" in title or plugin == "10015":
        return "generic.re-examine-cache-control-directives"
    if plugin == "10055" or "content security policy" in title or title.startswith("csp"):
        if "header not set" in title or "header fehlt" in title or "eksik" in title:
            return "missing-header-content-security-policy"
        if "wildcard" in title:
            return "generic.csp-wildcard-directive"
        if "script-src" in title:
            return "generic.csp-script-src-unsafe-inline"
        if "style-src" in title:
            return "generic.csp-style-src-unsafe-inline"
    if plugin == "10037" or "x-powered-by" in title:
        return "x-powered-by-disclosure"
    return rule or (finding.correlation_key or "")
