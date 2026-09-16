"""Build report-facing evidence and impact text from stored finding fields."""

from __future__ import annotations

from app.i18n.report_strings import Locale
from app.models.finding import Finding
from app.security.evidence_sanitizer import sanitize_evidence_dict
from app.services.finding_evidence import normalize_finding_evidence
from app.services.pdf_utils import wrap_text_for_pdf
from app.services.report_catalog_keys import report_catalog_key


def _evidence_missing(locale: Locale) -> str:
    if locale == "de":
        return "Für diesen Scan wurden keine detaillierten Nachweise gespeichert. Neuer Scan empfohlen."
    return "Bu taramada ayrıntılı kanıt kaydedilmedi. Yeni tarama önerilir."


def format_evidence_for_report(finding: Finding, locale: Locale) -> str:
    raw = sanitize_evidence_dict(finding.evidence)
    if not raw:
        return _evidence_missing(locale)
    raw = normalize_finding_evidence(
        raw,
        source_tool=finding.source_tool,
        source_rule_id=finding.source_rule_id or finding.correlation_key,
    )
    if not raw:
        return _evidence_missing(locale)

    lines: list[str] = []
    etype = raw.get("evidence_type")
    conflicts = raw.get("evidence_conflicts")

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
        _append_common(lines, finding, locale)
        _append_conflicts(lines, conflicts, locale)
        return wrap_text_for_pdf("\n".join(lines))

    if raw.get("expires_at") or finding.source_rule_id == "cert-expiring-soon":
        expires = raw.get("expires_at")
        days = raw.get("days_left")
        threshold = raw.get("warning_threshold_days")
        if locale == "de":
            if expires:
                lines.append(f"Ablauf (Beobachtungszeitpunkt): {expires}")
            if days is not None:
                lines.append(f"Volle Tage bei Beobachtung: {days}")
            if threshold is not None:
                lines.append(
                    f"Warnschwelle laut Scan-Datensatz: {threshold} Tage "
                    "(nicht der aktuelle Plattform-Default, falls er später geändert wurde)"
                )
            else:
                lines.append("Warnschwelle: in diesem Datensatz nicht gespeichert")
            lines.append(f"Quelle: {finding.source_tool or 'tls_check'}")
            if finding.source_rule_id:
                lines.append(f"Regel: {finding.source_rule_id}")
        else:
            if expires:
                lines.append(f"Bitiş (gözlem anı): {expires}")
            if days is not None:
                lines.append(f"Tarama gözlem anında kalan (tam gün): {days}")
            if threshold is not None:
                lines.append(
                    f"Taramada kaydedilen uyarı eşiği: {threshold} gün "
                    "(sonradan değişmiş olsa bile rapor anındaki varsayılan değil)"
                )
            else:
                lines.append("Uyarı eşiği: bu kayıtta saklanmamış")
            lines.append(f"Kaynak: {finding.source_tool or 'tls_check'}")
            if finding.source_rule_id:
                lines.append(f"Kural: {finding.source_rule_id}")
        if finding.affected_url:
            lines.append(f"URL: {finding.affected_url}")
        _append_conflicts(lines, conflicts, locale)
        return wrap_text_for_pdf("\n".join(lines) if lines else _evidence_missing(locale))

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
        _append_conflicts(lines, conflicts, locale)
        return wrap_text_for_pdf("\n".join(lines))

    return _evidence_missing(locale)


def enrich_risk_explanation(finding: Finding, locale: Locale) -> str | None:
    if finding.risk_explanation and not _is_placeholder_risk(finding):
        return finding.risk_explanation
    evidence = normalize_finding_evidence(
        finding.evidence or {},
        source_tool=finding.source_tool,
        source_rule_id=finding.source_rule_id or finding.correlation_key,
    )
    catalog_key = report_catalog_key(finding)
    policy = (
        evidence.get("policy")
        or evidence.get("csp")
        or (
            evidence.get("header_value")
            if "content-security-policy" in str(evidence.get("header_name") or "").lower()
            else None
        )
    )
    if catalog_key == "generic.csp-wildcard-directive":
        return _csp_wildcard_risk(policy, locale)
    if catalog_key == "generic.csp-script-src-unsafe-inline":
        return _csp_script_risk(policy, locale)
    if catalog_key == "generic.csp-style-src-unsafe-inline":
        return _csp_style_risk(policy, locale)
    if catalog_key == "generic.re-examine-cache-control-directives":
        return _cache_risk(evidence.get("header_value"), locale)
    return finding.description


def _is_placeholder_risk(finding: Finding) -> bool:
    risk = (finding.risk_explanation or "").strip()
    title = (finding.title or "").strip()
    if not risk or risk == title:
        return True
    return bool(title and (risk.startswith(f"{title} —") or risk.startswith(f"{title} -")))


def _append_common(lines: list[str], finding: Finding, locale: Locale) -> None:
    if finding.affected_url:
        lines.append(f"URL: {finding.affected_url}")
    if finding.source_tool:
        lines.append(f"Kaynak: {finding.source_tool}" if locale != "de" else f"Quelle: {finding.source_tool}")
    if finding.source_rule_id:
        lines.append(
            f"Kural: {finding.source_rule_id}" if locale != "de" else f"Regel: {finding.source_rule_id}"
        )


def _append_conflicts(lines: list[str], conflicts: object, locale: Locale) -> None:
    if not isinstance(conflicts, dict) or not conflicts:
        return
    for field, rows in conflicts.items():
        if not isinstance(rows, list):
            continue
        rendered = "; ".join(
            f"{row.get('origin', '?')}={row.get('value')}" for row in rows if isinstance(row, dict)
        )
        if locale == "de":
            lines.append(f"Quellenkonflikt bei {field} (keine stille Auswahl): {rendered}")
        else:
            lines.append(f"Kaynak çelişkisi ({field}; sessiz seçim yok): {rendered}")


def _csp_wildcard_risk(policy: str | None, locale: Locale) -> str:
    extra = _wildcard_note(policy, locale)
    if locale == "de":
        base = (
            "CSP erlaubt weite Quellen. Das ist ein Konfigurationshinweis, kein bestätigtes XSS."
        )
        if policy:
            return f"{base} Beobachtete Policy: {policy}. {extra}".strip()
        return f"{base} Vollständige Policy fehlt in diesem Datensatz. {extra}".strip()
    base = "CSP geniş kaynak izni içeriyor. Bu yapılandırma uyarısıdır; doğrulanmış XSS değildir."
    if policy:
        return f"{base} Gözlenen politika: {policy}. {extra}".strip()
    return f"{base} Tam politika bu kayıtta yok. {extra}".strip()


def _csp_script_risk(policy: str | None, locale: Locale) -> str:
    if locale == "de":
        text = (
            "script-src unsafe-inline erlaubt Inline-JavaScript. "
            "Wirkung unterscheidet sich von style-src unsafe-inline. Kein nachgewiesenes XSS."
        )
        return f"{text} Policy: {policy}" if policy else text
    text = (
        "script-src unsafe-inline satır içi JavaScript'e izin verir. "
        "Etkisi style-src unsafe-inline'dan farklıdır. Doğrulanmış XSS değildir."
    )
    return f"{text} Politika: {policy}" if policy else text


def _csp_style_risk(policy: str | None, locale: Locale) -> str:
    if locale == "de":
        text = (
            "style-src unsafe-inline erlaubt Inline-CSS (Style-Injection), "
            "nicht dasselbe wie ausführbares Inline-Skript. Kein bestätigtes XSS."
        )
        return f"{text} Policy: {policy}" if policy else text
    text = (
        "style-src unsafe-inline satır içi CSS'e izin verir (stil enjeksiyonu); "
        "çalıştırılabilir satır içi script ile aynı etki değildir. Doğrulanmış XSS değildir."
    )
    return f"{text} Politika: {policy}" if policy else text


def _cache_risk(value: object, locale: Locale) -> str:
    observed = str(value or "").strip()
    if locale == "de":
        text = (
            "Cache-Control steuert Zwischenspeicherung. "
            "s-maxage allein ist kein Nachweis eines Datenlecks; Sensitivität unbekannt."
        )
        return f"{text} Beobachtet: {observed}" if observed else text
    text = (
        "Cache-Control önbelleği yönetir. "
        "s-maxage tek başına veri sızıntısı kanıtı değildir; yanıt hassasiyeti bu kayıtta bilinmiyor."
    )
    return f"{text} Gözlenen: {observed}" if observed else text


def _wildcard_note(policy: str | None, locale: Locale) -> str:
    if not policy:
        return (
            "Ohne Policy-Text kann literal * nicht behauptet werden."
            if locale == "de"
            else "Politika metni yokken literal `*` olduğu yazılamaz."
        )
    has_star = "*" in policy
    if has_star:
        return (
            "Literal * kommt in der gespeicherten Policy vor."
            if locale == "de"
            else "Kayıtlı politikada literal `*` var."
        )
    if any(token in policy.lower() for token in ("https:", "http:", "data:", "blob:")):
        return (
            "Keine literale *; beobachtbar sind weite Schema-Quellen."
            if locale == "de"
            else "Literal `*` yok; gözlenen geniş şema izinleridir."
        )
    return (
        "Keine literale * in der gespeicherten Policy."
        if locale == "de"
        else "Kayıtlı politikada literal `*` yok."
    )
