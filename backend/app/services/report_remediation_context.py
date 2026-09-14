"""Context-aware remediation text for reports (no generic misapplied fixes)."""

from __future__ import annotations

from app.i18n.report_strings import Locale
from app.models.finding import Finding


def _server_value(evidence: dict) -> str:
    return str(evidence.get("server") or evidence.get("header_value") or "").strip()


def _powered_by_value(evidence: dict) -> str:
    return str(
        evidence.get("x_powered_by") or evidence.get("header_value") or ""
    ).strip()


def _has_version_token(value: str) -> bool:
    lowered = value.lower()
    if "/" in value:
        return True
    for token in ("nginx/", "apache/", "microsoft-iis/"):
        if token in lowered:
            return True
    return False


def contextual_remediation(finding: Finding, locale: Locale) -> tuple[str | None, list | None, str | None]:
    """Return (remediation, steps, config_snippet) overrides or Nones to keep stored values."""
    rule = finding.source_rule_id or ""
    evidence = finding.evidence or {}

    if rule == "server-disclosure":
        server = _server_value(evidence)
        has_version = _has_version_token(server)
        if locale == "de":
            summary = (
                "Server-Header reduziert Angriffsfläche; reine Produktnamen ohne Version sind "
                "häufig harmlos."
            )
            steps = [
                "Prüfen, ob im Header eine Versionsnummer sichtbar ist (z. B. nginx/1.24).",
            ]
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
                    "Apache: ServerTokens Prod, ServerSignature Off (nur bei Apache).",
                    "Nach Änderung erneut scannen und den Server-Header vergleichen.",
                ]
            )
            snippet = "server_tokens off;" if has_version else None
            return summary, steps, snippet

        summary = (
            "Server başlığı saldırganlara ipucu verebilir; yalnızca ürün adı (sürümsüz) genelde düşük risklidir."
        )
        steps = [
            "Başlıkta sürüm numarası var mı kontrol edin (ör. nginx/1.24).",
        ]
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
                "Apache ise: ServerTokens Prod, ServerSignature Off.",
                "Değişiklik sonrası yeniden tarayıp Server başlığını doğrulayın.",
            ]
        )
        snippet = "server_tokens off;" if has_version else None
        return summary, steps, snippet

    if rule == "x-powered-by-disclosure":
        powered = _powered_by_value(evidence).lower()
        if locale == "de":
            summary = "X-Powered-By zeigt oft Middleware/Hosting (Passenger, Plesk, PHP) — nicht immer PHP expose_php."
            steps = [
                f"Beobachteter Wert: {powered or '—'}",
                "Welche Schicht den Header setzt, ist ohne Server-Zugriff oft unklar — Proxy-, App- und Panel-Einstellungen prüfen.",
            ]
            if "passenger" in powered or "plesk" in powered:
                steps.append(
                    "Passenger/Plesk: Header in Plesk/Passenger- oder Reverse-Proxy-Konfiguration entfernen "
                    "(z. B. proxy_hide_header X-Powered-By; nur wenn Nginx davor liegt)."
                )
            if "php" in powered:
                steps.append("PHP: expose_php = Off in php.ini.")
            steps.append("Nach Anpassung erneut scannen und den Header vergleichen.")
            return summary, steps, None

        summary = (
            "X-Powered-By genelde uygulama veya barındırma katmanını gösterir; her zaman PHP kaynaklı değildir."
        )
        steps = [
            f"Gözlemlenen değer: {powered or '—'}",
            "Başlığı hangi katmanın eklediği sunucu erişimi olmadan kesin bilinmeyebilir — proxy, uygulama ve panel ayarlarını kontrol edin.",
        ]
        if "passenger" in powered or "plesk" in powered:
            steps.append(
                "Passenger/Plesk: Plesk/Passenger veya önündeki reverse proxy ayarlarından header kaldırın "
                "(Nginx önünde ise proxy_hide_header X-Powered-By; yalnızca ilgili katmanda)."
            )
        if "php" in powered:
            steps.append("PHP kaynaklıysa: php.ini içinde expose_php = Off.")
        steps.append("Değişiklik sonrası yeniden tarayıp başlığı doğrulayın.")
        return summary, steps, None

    if rule == "cert-expiring-soon":
        days = evidence.get("days_left")
        threshold = evidence.get("warning_threshold_days")
        if locale == "de":
            summary = finding.remediation or "TLS-Zertifikat vor Ablauf erneuern."
            steps = list(finding.remediation_steps or [])
            if threshold is not None:
                steps.insert(
                    0,
                    f"Warnschwelle dieser Plattform: {threshold} volle Tage vor Ablauf "
                    f"(Beobachtung: {days if days is not None else '—'} Tage verbleibend).",
                )
            return summary, steps or None, finding.config_snippet

        summary = finding.remediation or "TLS sertifikasını süre dolmadan yenileyin."
        steps = list(finding.remediation_steps or [])
        if threshold is not None:
            steps.insert(
                0,
                f"Platform uyarı eşiği: {threshold} tam gün (gözlem: "
                f"{days if days is not None else '—'} gün kaldı).",
            )
        return summary, steps or None, finding.config_snippet

    return None, None, None
