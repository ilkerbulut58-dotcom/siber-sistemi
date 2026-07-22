"""Passive detection of exposed passwords, payment, and banking data in public responses."""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

import httpx

from app.scanners.base import RawFinding

logger = logging.getLogger(__name__)

MAX_BODY = 250_000

PATTERNS: list[tuple[str, str, re.Pattern[str], str]] = [
    (
        "hardcoded-password",
        "Possible hardcoded password in public response",
        re.compile(
            r"(?i)(password|passwd|pwd|sifre|şifre)\s*[:=]\s*['\"]([^'\"\\s]{4,})['\"]"
        ),
        "high",
    ),
    (
        "db-connection-string",
        "Possible database connection string with credentials",
        re.compile(
            r"(?i)(mysql|postgres|mongodb|redis)://[^\s'\"<>]{8,}",
        ),
        "critical",
    ),
    (
        "turkish-iban",
        "Possible Turkish IBAN exposed in response",
        re.compile(r"\bTR[0-9]{2}(?:\s?[0-9]{4}){5}\s?[0-9]{2}\b", re.IGNORECASE),
        "critical",
    ),
    (
        "generic-iban",
        "Possible IBAN exposed in response",
        re.compile(r"\b[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}\b"),
        "high",
    ),
    (
        "credit-card-number",
        "Possible payment card number in public response",
        re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
        "critical",
    ),
    (
        "bank-account-hint",
        "Possible bank account reference in response",
        re.compile(
            r"(?i)(hesap\s*(?:no|numarasi|numarası)|account\s*(?:no|number)|iban)\s*[:=]\s*['\"]?[\w\d\s-]{6,}"
        ),
        "high",
    ),
    (
        "api-secret-assignment",
        "Possible API secret in public response",
        re.compile(
            r"(?i)(client_secret|api_secret|private_key|access_token)\s*[:=]\s*['\"][^'\"]{8,}['\"]"
        ),
        "high",
    ),
]

JS_PATHS = ("/main.js", "/app.js", "/static/js/main.js", "/bundle.js", "/env.js")


def _luhn_valid(digits: str) -> bool:
    if len(digits) < 13 or len(digits) > 19:
        return False
    total = 0
    reverse = digits[::-1]
    for i, ch in enumerate(reverse):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _mask_sample(text: str, *, keep: int = 4) -> str:
    compact = text.strip()
    if len(compact) <= keep * 2:
        return "*" * len(compact)
    return f"{compact[:keep]}…{compact[-keep:]}"


def _match_finding(
    *,
    rule_id: str,
    title: str,
    severity: str,
    url: str,
    sample: str,
) -> RawFinding:
    return RawFinding(
        source_tool="sensitive_data",
        source_rule_id=f"sensitive-{rule_id}",
        title=title,
        description=(
            f"Pattern '{rule_id}' matched in public response from {url}. "
            "Manual verification required — may be a false positive."
        ),
        severity=severity,
        affected_url=url,
        remediation="Remove sensitive data from public pages/scripts and rotate exposed credentials.",
        evidence={"pattern": rule_id, "masked_sample": _mask_sample(sample)},
    )


async def scan_sensitive_data(target_url: str) -> list[RawFinding]:
    findings: list[RawFinding] = []
    parsed = urlparse(target_url)
    if not parsed.scheme or not parsed.netloc:
        return []

    urls = [target_url, *{f"{parsed.scheme}://{parsed.netloc}{p}" for p in JS_PATHS}]

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for url in urls:
            try:
                response = await client.get(url)
            except httpx.HTTPError as exc:
                logger.debug("Sensitive data scan skipped for %s: %s", url, exc)
                continue
            if response.status_code >= 400:
                continue

            content_type = response.headers.get("content-type", "").lower()
            if not any(t in content_type for t in ("text/", "json", "javascript", "xml")) and not url.endswith(
                ".js"
            ):
                continue

            body = response.text[:MAX_BODY]
            seen_rules: set[str] = set()

            for rule_id, title, pattern, severity in PATTERNS:
                if rule_id in seen_rules:
                    continue
                match = pattern.search(body)
                if not match:
                    continue

                sample = match.group(0)
                if rule_id == "credit-card-number":
                    digits = re.sub(r"\D", "", sample)
                    if not _luhn_valid(digits):
                        continue
                    sample = digits[:6] + "******" + digits[-4:]

                if rule_id == "generic-iban" and re.match(r"^TR", sample, re.I):
                    continue

                findings.append(
                    _match_finding(
                        rule_id=rule_id,
                        title=title,
                        severity=severity,
                        url=url,
                        sample=sample,
                    )
                )
                seen_rules.add(rule_id)

    return findings
