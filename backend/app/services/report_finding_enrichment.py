"""Build report-facing evidence and impact text from stored finding fields."""

from __future__ import annotations

import json
from typing import Any

from app.i18n.report_strings import Locale
from app.models.finding import Finding
from app.security.evidence_sanitizer import sanitize_evidence_dict


def _evidence_missing(locale: Locale) -> str:
    if locale == "de":
        return "Für diesen Scan wurden keine detaillierten Nachweise gespeichert. Neuer Scan empfohlen."
    return "Bu taramada ayrıntılı kanıt kaydedilmedi. Yeni tarama önerilir."


def format_evidence_for_report(finding: Finding, locale: Locale) -> str:
    raw = sanitize_evidence_dict(finding.evidence)
    if not raw:
        return _evidence_missing(locale)

    lines: list[str] = []
    if raw.get("evidence_type") == "http_header" and raw.get("header_value"):
        name = raw.get("header_name") or "Header"
        lines.append(f"{name}: {raw['header_value']}")
    if header := raw.get("missing_header"):
        lines.append(f"Header: {header} (missing)")
    if powered := raw.get("x_powered_by"):
        lines.append(f"X-Powered-By: {powered}")
    if server := raw.get("server"):
        lines.append(f"Server: {server}")
    if expires := raw.get("expires_at"):
        days = raw.get("days_left")
        if locale == "de":
            lines.append(f"Zertifikat gültig bis: {expires}" + (f" ({days} Tage)" if days is not None else ""))
        else:
            lines.append(f"Sertifika bitiş: {expires}" + (f" ({days} gün kaldı)" if days is not None else ""))
    if status_code := raw.get("status_code"):
        lines.append(f"HTTP status: {status_code}")
    if matcher := raw.get("matcher"):
        lines.append(f"Matcher: {matcher}")

    if not lines:
        try:
            compact = json.dumps(raw, ensure_ascii=False, indent=2)
        except TypeError:
            compact = str(raw)
        if len(compact) > 4000:
            compact = compact[:4000] + "…"
        return compact
    return "\n".join(lines)


def enrich_risk_explanation(finding: Finding, locale: Locale) -> str | None:
    if finding.risk_explanation and finding.risk_explanation.strip() != finding.title.strip():
        return finding.risk_explanation
    evidence = finding.evidence or {}
    title_lower = (finding.title or "").lower()
    if locale == "de":
        if "csp" in title_lower or "content-security" in title_lower:
            policy = evidence.get("policy") or evidence.get("csp")
            if policy:
                return (
                    "Die beobachtete Content-Security-Policy enthält unsichere Direktiven. "
                    f"Policy-Ausschnitt: {policy}"
                )
            return (
                "Eine Content-Security-Policy-Schwäche wurde erkannt. "
                "Dies bedeutet nicht automatisch eine bestätigte XSS-Ausnutzung."
            )
        if "cache" in title_lower:
            return (
                "Cache-Control-Header sollten zum Inhaltstyp passen. "
                "Nicht jede Antwort benötigt no-store."
            )
    else:
        if "csp" in title_lower or "content-security" in title_lower:
            policy = evidence.get("policy") or evidence.get("csp")
            if policy:
                return (
                    "Gözlemlenen CSP politikasında riskli direktifler var. "
                    f"Policy: {policy}"
                )
            return (
                "CSP ile ilgili bir zayıflık tespit edildi; bu otomatik olarak doğrulanmış XSS anlamına gelmez."
            )
        if "cache" in title_lower:
            return (
                "Cache-Control başlığı içeriğin hassasiyetine göre değerlendirilmelidir. "
                "Her yanıt için no-store gerekmez."
            )
    return finding.description
