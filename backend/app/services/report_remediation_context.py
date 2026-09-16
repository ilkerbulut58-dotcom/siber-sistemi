"""Context-aware remediation text for reports (no generic misapplied fixes)."""

from __future__ import annotations

from app.i18n.report_strings import Locale
from app.models.finding import Finding
from app.services.finding_evidence import normalize_finding_evidence
from app.services.report_catalog_keys import report_catalog_key


def _server_value(evidence: dict) -> str:
    return str(evidence.get("server") or evidence.get("header_value") or "").strip()


def _powered_by_value(evidence: dict) -> str:
    return str(
        evidence.get("x_powered_by")
        or (
            evidence.get("header_value")
            if str(evidence.get("header_name") or "").lower() == "x-powered-by"
            else ""
        )
        or evidence.get("header_value")
        or ""
    ).strip()


def _policy_value(evidence: dict) -> str:
    header = str(evidence.get("header_name") or "").lower()
    if "content-security-policy" in header or not header:
        return str(
            evidence.get("policy")
            or evidence.get("csp")
            or evidence.get("header_value")
            or ""
        ).strip()
    return str(evidence.get("policy") or evidence.get("csp") or "").strip()


def _has_version_token(value: str) -> bool:
    lowered = value.lower()
    if "/" in value:
        return True
    return any(token in lowered for token in ("nginx/", "apache/", "microsoft-iis/"))


def _resolved_evidence(finding: Finding) -> dict:
    return normalize_finding_evidence(
        finding.evidence or {},
        source_tool=finding.source_tool,
        source_rule_id=finding.source_rule_id or finding.correlation_key,
    )


def contextual_remediation(finding: Finding, locale: Locale) -> tuple[str | None, list | None, str | None]:
    """Return (remediation, steps, config_snippet) overrides or Nones to keep stored values."""
    rule = report_catalog_key(finding)
    evidence = _resolved_evidence(finding)

    if rule == "server-disclosure":
        return _server_remediation(evidence, locale)
    if rule == "x-powered-by-disclosure":
        return _x_powered_by_remediation(evidence, locale)
    if rule == "cert-expiring-soon":
        return _cert_remediation(finding, evidence, locale)
    if rule == "generic.csp-wildcard-directive":
        return _csp_wildcard_remediation(evidence, locale)
    if rule == "generic.csp-script-src-unsafe-inline":
        return _csp_script_inline_remediation(evidence, locale)
    if rule == "generic.csp-style-src-unsafe-inline":
        return _csp_style_inline_remediation(evidence, locale)
    if rule == "generic.re-examine-cache-control-directives":
        return _cache_control_remediation(evidence, locale)
    return None, None, None


def _conflict_note(evidence: dict, locale: Locale) -> str | None:
    conflicts = evidence.get("evidence_conflicts")
    if not isinstance(conflicts, dict) or not conflicts:
        return None
    parts = []
    for field, rows in conflicts.items():
        if not isinstance(rows, list):
            continue
        rendered = "; ".join(
            f"{row.get('origin', '?')}={row.get('value')}" for row in rows if isinstance(row, dict)
        )
        parts.append(f"{field}: {rendered}")
    if not parts:
        return None
    joined = " | ".join(parts)
    if locale == "de":
        return f"Quellen widersprechen sich — nicht als einzige Wahrheit: {joined}"
    return f"Kaynaklar çelişiyor — tek gerçek gibi sunulmaz: {joined}"


def _server_remediation(evidence: dict, locale: Locale) -> tuple[str, list[str], str | None]:
    server = _server_value(evidence)
    has_version = _has_version_token(server)
    conflict = _conflict_note(evidence, locale)
    if locale == "de":
        summary = (
            "Server-Header reduziert Angriffsfläche; reine Produktnamen ohne Version sind "
            "häufig harmlos. Produktnamen zu entfernen ist nicht dasselbe wie die Version auszublenden."
        )
        steps = [
            f"Beobachteter Wert: {server or '—'}",
            "Prüfen, ob im Header eine Versionsnummer sichtbar ist (z. B. nginx/1.24).",
        ]
        if conflict:
            steps.insert(0, conflict)
        if has_version:
            steps.append(
                "Bei Nginx: server_tokens off; blendet die Versionsnummer aus, nicht zwingend den Namen nginx."
            )
        else:
            steps.append(
                "Bei nur nginx ohne Version: server_tokens off; ändert oft wenig am sichtbaren Produktnamen — "
                "CDN/Proxy-Einstellungen prüfen, falls der Name entfernt werden soll."
            )
        steps.extend(
            [
                "Apache-Schritte nur anwenden, wenn der beobachtete Header Apache ist.",
                "Nach Änderung erneut scannen und den Server-Header vergleichen.",
            ]
        )
        snippet = "server_tokens off;" if has_version else None
        return summary, steps, snippet

    summary = (
        "Server başlığı saldırganlara ipucu verebilir; yalnızca ürün adı (sürümsüz) genelde düşük risklidir. "
        "Sürüm gizleme ile ürün adını kaldırmak aynı şey değildir."
    )
    steps = [
        f"Gözlemlenen değer: {server or '—'}",
        "Başlıkta sürüm numarası var mı kontrol edin (ör. nginx/1.24).",
    ]
    if conflict:
        steps.insert(0, conflict)
    if has_version:
        steps.append(
            "Nginx kullanıyorsanız: server_tokens off; sürümü gizler, nginx adını her zaman kaldırmaz."
        )
    else:
        steps.append(
            "Yalnızca nginx görünüyorsa: server_tokens off; çoğu kurulumda ürün adı kalabilir — "
            "CDN/proxy panelinden header gizlemeyi değerlendirin."
        )
    steps.extend(
        [
            "Apache adımlarını yalnız gözlenen değer Apache ise uygulayın.",
            "Değişiklik sonrası yeniden tarayıp Server başlığını doğrulayın.",
        ]
    )
    snippet = "server_tokens off;" if has_version else None
    return summary, steps, snippet


def _x_powered_by_remediation(evidence: dict, locale: Locale) -> tuple[str, list[str], None]:
    powered = _powered_by_value(evidence)
    lowered = powered.lower()
    conflict = _conflict_note(evidence, locale)
    if locale == "de":
        summary = (
            "X-Powered-By zeigt oft Middleware/Hosting (Passenger, Plesk, PHP) — "
            "nicht immer PHP expose_php und nicht IIS, sofern der Wert das nicht belegt."
        )
        steps = [
            f"Beobachteter Wert: {powered or '—'}",
            "Welche Schicht den Header setzt, ist ohne Server-Zugriff oft unklar — Proxy-, App- und Panel-Einstellungen prüfen.",
        ]
        if conflict:
            steps.insert(0, conflict)
        if "passenger" in lowered or "plesk" in lowered:
            steps.append(
                "Passenger/Plesk: Header in Plesk/Passenger- oder Reverse-Proxy-Konfiguration entfernen "
                "(z. B. proxy_hide_header X-Powered-By; nur wenn Nginx davor liegt)."
            )
        if "php" in lowered:
            steps.append("PHP: expose_php = Off in php.ini — nur weil der Wert PHP nennt.")
        if "iis" in lowered or "asp.net" in lowered:
            steps.append("IIS/ASP.NET: Header nur entfernen, wenn der beobachtete Wert das belegt.")
        steps.append("Nach Anpassung erneut scannen und den Header vergleichen.")
        return summary, steps, None

    summary = (
        "X-Powered-By genelde uygulama veya barındırma katmanını gösterir; "
        "gözlenen değer Passenger/Plesk ise PHP veya IIS varsayılmaz."
    )
    steps = [
        f"Gözlemlenen değer: {powered or '—'}",
        "Başlığı hangi katmanın eklediği sunucu erişimi olmadan kesin bilinmeyebilir — proxy, uygulama ve panel ayarlarını kontrol edin.",
    ]
    if conflict:
        steps.insert(0, conflict)
    if "passenger" in lowered or "plesk" in lowered:
        steps.append(
            "Passenger/Plesk: Plesk/Passenger veya önündeki reverse proxy ayarlarından header kaldırın "
            "(Nginx önünde ise proxy_hide_header X-Powered-By; yalnızca ilgili katmanda)."
        )
    if "php" in lowered:
        steps.append("PHP kaynaklıysa (değer PHP içeriyorsa): php.ini içinde expose_php = Off.")
    if "iis" in lowered or "asp.net" in lowered:
        steps.append("IIS/ASP.NET adımlarını yalnız gözlenen değer bunu gösteriyorsa uygulayın.")
    steps.append("Değişiklik sonrası yeniden tarayıp başlığı doğrulayın.")
    return summary, steps, None


def _cert_remediation(finding: Finding, evidence: dict, locale: Locale) -> tuple[str, list | None, str | None]:
    days = evidence.get("days_left")
    threshold = evidence.get("warning_threshold_days")
    if locale == "de":
        summary = finding.remediation or "TLS-Zertifikat vor Ablauf erneuern."
        steps = list(finding.remediation_steps or [])
        if threshold is not None:
            steps.insert(
                0,
                f"Im Scan gespeicherte Warnschwelle: {threshold} volle Tage "
                f"(Beobachtung: {days if days is not None else '—'} Tage verbleibend). "
                "Kein nachträglich eingesetzter aktueller Standard.",
            )
        elif days is not None:
            steps.insert(
                0,
                f"Verbleibende volle Tage zum Beobachtungszeitpunkt: {days}. "
                "Schwelle war in diesem Datensatz nicht gespeichert.",
            )
        return summary, steps or None, finding.config_snippet

    summary = finding.remediation or "TLS sertifikasını süre dolmadan yenileyin."
    steps = list(finding.remediation_steps or [])
    if threshold is not None:
        steps.insert(
            0,
            f"Taramada kaydedilen uyarı eşiği: {threshold} tam gün (gözlem: "
            f"{days if days is not None else '—'} gün kaldı). "
            "Rapor anındaki güncel varsayılan değildir.",
        )
    elif days is not None:
        steps.insert(
            0,
            f"Gözlem anında kalan tam gün: {days}. Bu kayıtta eşik saklanmamış.",
        )
    return summary, steps or None, finding.config_snippet


def _csp_wildcard_remediation(evidence: dict, locale: Locale) -> tuple[str, list[str], None]:
    policy = _policy_value(evidence)
    has_star = "*" in policy
    has_scheme = any(token in policy.lower() for token in ("https:", "http:", "data:", "blob:"))
    if locale == "de":
        summary = (
            "Die beobachtete CSP erlaubt weite Quellen. Das ist keine bestätigte XSS-Ausnutzung. "
            "Eine generische CSP als alleinige Lösung kann die Seite brechen."
        )
        steps = [
            f"Beobachtete Policy: {policy or '— (vollständiger Text in diesem Datensatz nicht gespeichert)'}",
        ]
        if policy and not has_star:
            steps.append(
                "Im gespeicherten Text kommt kein literales * vor — nicht als Stern-Wildcard darstellen."
            )
        if has_scheme:
            steps.append(
                "Weite Schema-Quellen (z. B. https: / data: / blob:) sind von einem literalen * zu unterscheiden."
            )
        if has_star:
            steps.append("Literal * in der Policy gezielt auf benötigte Hosts einengen.")
        steps.extend(
            [
                "Nur die im Nachweis genannten Direktiven verengen; kein Copy-Paste einer Standard-CSP.",
                "Zuerst in Staging testen, dann erneut scannen.",
            ]
        )
        return summary, steps, None
    summary = (
        "Gözlenen CSP kaynak izni geniş. Bu, doğrulanmış XSS sömürüsü değildir. "
        "Tek bir genel CSP'yi kesin çözüm diye uygulamayın; site bozulabilir."
    )
    steps = [
        f"Gözlenen politika: {policy or '— (tam metin bu kayıtta yok)'}",
    ]
    if policy and not has_star:
        steps.append("Kayıtlı metinde literal `*` yok; yıldız kullanılmış gibi yazılmamalı.")
    if has_scheme:
        steps.append(
            "Geniş şema izni (ör. https: / data: / blob:) ile literal yıldız farklı şeylerdir."
        )
    if has_star:
        steps.append("Politikadaki literal `*` yalnızca gereken kökenlerle daraltılmalıdır.")
    steps.extend(
        [
            "Yalnız kanıtta görülen yönergeleri sıkılaştırın; hazır genel CSP kopyalamayın.",
            "Önce staging'de deneyin, sonra yeniden tarayın.",
        ]
    )
    return summary, steps, None


def _csp_script_inline_remediation(evidence: dict, locale: Locale) -> tuple[str, list[str], None]:
    policy = _policy_value(evidence)
    if locale == "de":
        return (
            "script-src enthält unsafe-inline: Inline-JavaScript wird erlaubt. "
            "Das ist ein CSP-Konfigurationshinweis, kein nachgewiesenes XSS.",
            [
                f"Beobachtete Policy: {policy or '—'}",
                "Inline-Skript von Inline-Styles trennen; style-src unsafe-inline ist ein anderes Risiko.",
                "Statt unsafe-inline Nonce oder Hash für Skripte prüfen — nur nach Inventar vorhandener Inline-Skripte.",
                "Keine universelle CSP als Drop-in; Staging zuerst, dann erneut scannen.",
            ],
            None,
        )
    return (
        "script-src içinde unsafe-inline var: satır içi JavaScript'e izin verir. "
        "Bu bir CSP yapılandırma uyarısıdır; doğrulanmış XSS değildir.",
        [
            f"Gözlenen politika: {policy or '—'}",
            "Satır içi script etkisini satır içi style'dan ayırın; style-src unsafe-inline farklı bir risktir.",
            "unsafe-inline yerine nonce veya hash'i, mevcut inline script envanterinden sonra değerlendirin.",
            "Hazır genel CSP uygulamayın; önce staging, sonra yeniden tarama.",
        ],
        None,
    )


def _csp_style_inline_remediation(evidence: dict, locale: Locale) -> tuple[str, list[str], None]:
    policy = _policy_value(evidence)
    if locale == "de":
        return (
            "style-src enthält unsafe-inline: Inline-CSS wird erlaubt. "
            "Das erleichtert Style-Injection, ist aber kein bestätigtes XSS durch Skripte.",
            [
                f"Beobachtete Policy: {policy or '—'}",
                "Nicht dieselbe Härtung wie bei script-src unsafe-inline annehmen.",
                "Nonce/Hash für Styles nur, wenn die Anwendung das unterstützt; sonst schrittweise verengen.",
                "Zuerst Staging, dann erneut scannen.",
            ],
            None,
        )
    return (
        "style-src içinde unsafe-inline var: satır içi CSS'e izin verir. "
        "Stil enjeksiyonunu kolaylaştırır; script XSS'i kanıtlamaz.",
        [
            f"Gözlenen politika: {policy or '—'}",
            "script-src unsafe-inline ile aynı düzeltmeyi varsaymayın.",
            "Uygulama destekliyorsa style için nonce/hash; değilse kademeli daraltın.",
            "Önce staging, sonra yeniden tarama.",
        ],
        None,
    )


def _cache_control_remediation(evidence: dict, locale: Locale) -> tuple[str, list[str], None]:
    value = str(evidence.get("header_value") or "").strip()
    if locale == "de":
        return (
            "Cache-Control beschreibt Caching, nicht automatisch eine Datenpanne. "
            "s-maxage allein belegt keinen Abfluss sensibler Daten.",
            [
                f"Beobachteter Wert: {value or '—'}",
                "Die Sensitivität dieser Antwort ist in diesem Datensatz nicht belegt — nicht als Leak darstellen.",
                "no-store nur für wirklich sensible Antworten setzen; öffentliche Assets dürfen cachen.",
                "Änderung in Staging prüfen und Header erneut vergleichen.",
            ],
            None,
        )
    return (
        "Cache-Control önbellek davranışını anlatır; tek başına veri sızıntısı kanıtı değildir. "
        "s-maxage değeri hassas veri aktığını kanıtlamaz.",
        [
            f"Gözlenen değer: {value or '—'}",
            "Bu yanıtın hassasiyeti bu kayıtta bilinmiyor; sızıntı gibi sunulmamalı.",
            "no-store yalnız gerçekten hassas yanıtlar için; genel varlıklar önbelleğe alınabilir.",
            "Staging'de değiştirip başlığı yeniden karşılaştırın.",
        ],
        None,
    )
