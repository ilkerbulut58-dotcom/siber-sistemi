"""Build report-facing evidence and impact text from stored finding fields."""

from __future__ import annotations

from app.i18n.report_strings import Locale
from app.models.finding import Finding
from app.security.evidence_sanitizer import sanitize_evidence_dict
from app.services.finding_evidence import flatten_finding_evidence


def _evidence_missing(locale: Locale) -> str:
    if locale == "de":
        return "Für diesen Scan wurden keine detaillierten Nachweise gespeichert. Neuer Scan empfohlen."
    return "Bu taramada ayrıntılı kanıt kaydedilmedi. Yeni tarama önerilir."


def format_evidence_for_report(finding: Finding, locale: Locale) -> str:
    raw = sanitize_evidence_dict(finding.evidence)
    if not raw:
        return _evidence_missing(locale)
    raw = flatten_finding_evidence(
        raw,
        source_tool=finding.source_tool,
        source_rule_id=finding.source_rule_id or finding.correlation_key,
    )
    if not raw:
        return _evidence_missing(locale)

    lines: list[str] = []
    etype = raw.get("evidence_type")

    if etype == "http_header" or raw.get("header_name"):
        name = raw.get("header_name") or "Header"
        val = raw.get("header_value") or raw.get("server") or raw.get("x_powered_by")
        if locale == "de":
            lines.append(f"Kopfzeile: {name}")
            lines.append(f"Beobachteter Wert: {val or '—'}")
            lines.append("Nachweistyp: HTTP-Antwortheader")
        else:
            lines.append(f"Başlık adı: {name}")
            lines.append(f"Gözlenen değer: {val or '—'}")
            lines.append("Kanıt türü: HTTP yanıt başlığı")
        if finding.affected_url:
            lines.append(f"URL: {finding.affected_url}")
        if finding.source_tool:
            lines.append(f"Kaynak: {finding.source_tool}" if locale != "de" else f"Quelle: {finding.source_tool}")
        if finding.source_rule_id:
            lines.append(
                f"Kural: {finding.source_rule_id}" if locale != "de" else f"Regel: {finding.source_rule_id}"
            )
        return "\n".join(lines)

    if raw.get("expires_at") or finding.source_rule_id == "cert-expiring-soon":
        expires = raw.get("expires_at")
        days = raw.get("days_left")
        threshold = raw.get("warning_threshold_days")
        if locale == "de":
            if expires:
                lines.append(f"Ablauf: {expires}")
            if days is not None:
                lines.append(f"Volle Tage bei Beobachtung: {days}")
            if threshold is not None:
                lines.append(f"Warnschwelle (Plattform): {threshold} Tage")
            lines.append(f"Quelle: {finding.source_tool or 'tls_check'}")
            if finding.source_rule_id:
                lines.append(f"Regel: {finding.source_rule_id}")
        else:
            if expires:
                lines.append(f"Bitiş: {expires}")
            if days is not None:
                lines.append(f"Tarama anında kalan (tam gün): {days}")
            if threshold is not None:
                lines.append(f"Uyarı eşiği (platform): {threshold} gün")
            lines.append(f"Kaynak: {finding.source_tool or 'tls_check'}")
            if finding.source_rule_id:
                lines.append(f"Kural: {finding.source_rule_id}")
        if finding.affected_url:
            lines.append(f"URL: {finding.affected_url}")
        return "\n".join(lines) if lines else _evidence_missing(locale)

    if powered := raw.get("x_powered_by"):
        lines.append(f"X-Powered-By: {powered}")
    if server := raw.get("server"):
        lines.append(f"Server: {server}")
    if raw.get("missing_header"):
        lines.append(f"Header: {raw['missing_header']} (missing)")
    if status_code := raw.get("status_code"):
        lines.append(f"HTTP status: {status_code}")
    if matcher := raw.get("matcher"):
        if locale == "de":
            lines.append(f"Matcher (kein vollständiger Header-Nachweis): {matcher}")
        else:
            lines.append(f"Matcher (tam HTTP başlık kanıtı değil): {matcher}")

    if lines:
        return "\n".join(lines)

    return _evidence_missing(locale)


def enrich_risk_explanation(finding: Finding, locale: Locale) -> str | None:
    if finding.risk_explanation and finding.risk_explanation.strip() != finding.title.strip():
        return finding.risk_explanation
    evidence = flatten_finding_evidence(
        finding.evidence or {},
        source_tool=finding.source_tool,
        source_rule_id=finding.source_rule_id or finding.correlation_key,
    )
    title_lower = (finding.title or "").lower()
    if locale == "de":
        if "csp" in title_lower or "content-security" in title_lower:
            policy = evidence.get("policy") or evidence.get("csp")
            extra = _csp_risk_note(policy, locale)
            if policy:
                return (
                    "Die beobachtete Content-Security-Policy enthält riskante Direktiven. "
                    f"Policy: {policy}. {extra}"
                )
            return (
                "Eine Content-Security-Policy-Schwäche wurde erkannt — kein bestätigtes XSS. "
                + extra
            )
        if "cache" in title_lower:
            return (
                "Cache-Control-Header sollten zum Inhaltstyp passen. "
                "Nicht jede Antwort benötigt no-store."
            )
    else:
        if "csp" in title_lower or "content-security" in title_lower:
            policy = evidence.get("policy") or evidence.get("csp")
            extra = _csp_risk_note(policy, locale)
            if policy:
                return f"Gözlemlenen CSP: {policy}. {extra}"
            return (
                "CSP ile ilgili bir zayıflık tespit edildi; doğrulanmış XSS değildir. " + extra
            )
        if "cache" in title_lower:
            return (
                "Cache-Control başlığı içeriğin hassasiyetine göre değerlendirilmelidir. "
                "Her yanıt için no-store gerekmez."
            )
    return finding.description


def _csp_risk_note(policy: str | None, locale: Locale) -> str:
    if not policy:
        if locale == "de":
            return "Keine vollständige Policy im Scan-Nachweis gespeichert."
        return "Tam policy metni bu taramada kaydedilmedi."
    lowered = policy.lower()
    notes: list[str] = []
    if "unsafe-inline" in lowered:
        notes.append(
            "unsafe-inline erlaubt Inline-Skripte/Stile (höheres XSS-Risiko bei anderen Schwächen)."
            if locale == "de"
            else "unsafe-inline satır içi script/stil riskini artırır (tek başına sızma kanıtı değildir)."
        )
    if "*" in lowered and "script-src" in lowered:
        notes.append(
            "Wildcard in script-src erweitert erlaubte Skript-Quellen stark."
            if locale == "de"
            else "script-src içinde wildcard izin verilen kaynakları genişletir."
        )
    if not notes:
        return ""
    return " ".join(notes)
