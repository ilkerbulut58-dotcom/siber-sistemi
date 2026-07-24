"""Report template strings (TR / DE)."""

from __future__ import annotations

from typing import Literal

Locale = Literal["tr", "de"]


def normalize_locale(locale: str | None) -> Locale:
    return "de" if locale == "de" else "tr"


PROFILE_LABELS: dict[Locale, dict[str, str]] = {
    "tr": {
        "safe": "Güvenli Tarama",
        "deep": "Derin Tarama",
        "code": "Kod / Dosya Taraması",
    },
    "de": {
        "safe": "Sicherer Scan",
        "deep": "Tiefenscan",
        "code": "Code / Datei-Scan",
    },
}

STATUS_LABELS: dict[Locale, dict[str, str]] = {
    "tr": {
        "queued": "Kuyrukta",
        "validating": "Doğrulanıyor",
        "running": "Taranıyor",
        "parsing": "Analiz ediliyor",
        "completed": "Tamamlandı",
        "failed": "Başarısız",
        "cancelled": "İptal",
    },
    "de": {
        "queued": "In Warteschlange",
        "validating": "Wird validiert",
        "running": "Scan läuft",
        "parsing": "Wird analysiert",
        "completed": "Abgeschlossen",
        "failed": "Fehlgeschlagen",
        "cancelled": "Abgebrochen",
    },
}

SEVERITY_LABELS: dict[Locale, dict[str, str]] = {
    "tr": {
        "critical": "Kritik",
        "high": "Yüksek",
        "medium": "Orta",
        "low": "Düşük",
        "info": "Bilgi",
    },
    "de": {
        "critical": "Kritisch",
        "high": "Hoch",
        "medium": "Mittel",
        "low": "Niedrig",
        "info": "Info",
    },
}

FINDING_STATUS_LABELS: dict[Locale, dict[str, str]] = {
    "tr": {
        "open": "Açık",
        "resolved": "Giderildi",
        "false_positive": "Yanlış alarm",
        "accepted_risk": "Kabul edilen risk",
        "inconclusive": "Belirsiz",
    },
    "de": {
        "open": "Offen",
        "resolved": "Behoben",
        "false_positive": "Fehlalarm",
        "accepted_risk": "Akzeptiertes Risiko",
        "inconclusive": "Unklar",
    },
}

SCAN_REPORT_LABELS: dict[Locale, dict[str, str]] = {
    "tr": {
        "page_title": "SIBER Tarama Raporu",
        "report_title": "SIBER Güvenlik Tarama Raporu",
        "target": "Hedef",
        "profile": "Profil",
        "status": "Durum",
        "scan_id": "Tarama ID",
        "completed_at": "Tamamlanma",
        "total_findings": "Toplam bulgu",
        "summary": "Özet",
        "findings": "Bulgular",
        "what_it_means": "Ne anlama geliyor?",
        "solution": "Çözüm",
        "url": "URL",
        "no_findings": "Bu taramada bulgu tespit edilmedi.",
        "footer": "SIBER Security Analysis Platform",
    },
    "de": {
        "page_title": "SIBER Scan-Bericht",
        "report_title": "SIBER Sicherheits-Scan-Bericht",
        "target": "Ziel",
        "profile": "Profil",
        "status": "Status",
        "scan_id": "Scan-ID",
        "completed_at": "Abgeschlossen",
        "total_findings": "Befunde gesamt",
        "summary": "Zusammenfassung",
        "findings": "Befunde",
        "what_it_means": "Was bedeutet das?",
        "solution": "Lösung",
        "url": "URL",
        "no_findings": "In diesem Scan wurden keine Befunde erkannt.",
        "footer": "SIBER Security Analysis Platform",
    },
}

MOBILE_REPORT_LABELS: dict[Locale, dict[str, str]] = {
    "tr": {
        "page_title": "SIBER Mobil Güvenlik Raporu",
        "report_title": "SIBER Mobil Uygulama Güvenlik Raporu",
        "application": "Uygulama",
        "package": "Paket",
        "platform": "Platform",
        "version": "Sürüm",
        "security_score": "Güvenlik skoru",
        "analyzed_at": "Analiz tarihi",
        "report_generated": "Rapor",
        "summary": "Özet",
        "findings": "Bulgular",
        "component": "Bileşen",
        "recommendation": "Öneri",
        "no_findings": "Statik analiz sonucunda bulgu tespit edilmedi.",
        "scope_title": "Test kapsamı ve sınırlamalar",
        "limitation_1": "Yalnızca statik APK dosya analizi uygulanmıştır.",
        "limitation_2": "Dinamik saldırı, kod çalıştırma, cihaz istismarı veya runtime manipülasyonu yapılmamıştır.",
        "limitation_3": "Secret pattern eşleşmeleri false positive içerebilir; manuel doğrulama önerilir.",
        "limitation_4": "Bu rapor bir penetrasyon testi sertifikası veya uyumluluk garantisi değildir.",
        "limitation_5": "Detaylı kapsam: docs/customer-scope-and-limits.md",
    },
    "de": {
        "page_title": "SIBER Mobile-Sicherheitsbericht",
        "report_title": "SIBER Mobile App-Sicherheitsbericht",
        "application": "Anwendung",
        "package": "Paket",
        "platform": "Plattform",
        "version": "Version",
        "security_score": "Sicherheitswert",
        "analyzed_at": "Analysedatum",
        "report_generated": "Bericht",
        "summary": "Zusammenfassung",
        "findings": "Befunde",
        "component": "Komponente",
        "recommendation": "Empfehlung",
        "no_findings": "Bei der statischen Analyse wurden keine Befunde erkannt.",
        "scope_title": "Testumfang und Einschränkungen",
        "limitation_1": "Es wurde nur eine statische APK-Dateianalyse durchgeführt.",
        "limitation_2": "Kein dynamischer Angriff, Code-Ausführung, Geräteausnutzung oder Runtime-Manipulation.",
        "limitation_3": "Secret-Pattern-Treffer können Fehlalarme sein; manuelle Prüfung empfohlen.",
        "limitation_4": "Dieser Bericht ist kein Penetrationstest-Zertifikat oder Compliance-Garantie.",
        "limitation_5": "Detaillierter Umfang: docs/customer-scope-and-limits.md",
    },
}

MOBILE_JSON_LIMITATIONS: dict[Locale, list[str]] = {
    "tr": [
        "Dinamik runtime analizi veya kod çalıştırma yok",
        "Binary manifest ayrıştırması yapılmadı (metin tabanlı statik kontroller)",
        "Bu sürümde iOS IPA desteklenmiyor",
    ],
    "de": [
        "Keine dynamische Runtime-Analyse oder Code-Ausführung",
        "Kein Binary-Manifest-Parsing (textbasierte statische Prüfungen)",
        "iOS IPA in dieser Version nicht unterstützt",
    ],
}


def scan_risk_summary(locale: Locale, counts: dict[str, int]) -> str:
    if (counts.get("critical") or 0) > 0 or (counts.get("high") or 0) > 0:
        return (
            "Yüksek öncelikli bulgular var — en kısa sürede inceleyin."
            if locale == "tr"
            else "Hochprioritäre Befunde — bitte umgehend prüfen."
        )
    if (counts.get("medium") or 0) > 0:
        return (
            "Orta seviye iyileştirmeler önerilir."
            if locale == "tr"
            else "Mittlere Verbesserungen werden empfohlen."
        )
    if (counts.get("low") or 0) + (counts.get("info") or 0) > 0:
        return (
            "Kritik sorun yok; küçük iyileştirmeler yapılabilir."
            if locale == "tr"
            else "Keine kritischen Probleme; kleinere Verbesserungen möglich."
        )
    return (
        "Önemli bir sorun tespit edilmedi."
        if locale == "tr"
        else "Keine wesentlichen Probleme festgestellt."
    )


def mobile_risk_summary(
    locale: Locale,
    counts: dict[str, int],
    security_score: float | None,
) -> str:
    if (counts.get("critical") or 0) > 0 or (counts.get("high") or 0) > 0:
        return (
            "Yüksek öncelikli mobil güvenlik bulguları tespit edildi."
            if locale == "tr"
            else "Hochprioritäre mobile Sicherheitsbefunde erkannt."
        )
    if (counts.get("medium") or 0) > 0:
        return (
            "Orta seviye mobil güvenlik iyileştirmeleri önerilir."
            if locale == "tr"
            else "Mittlere mobile Sicherheitsverbesserungen empfohlen."
        )
    if security_score is not None and security_score >= 80:
        return (
            "Mobil güvenlik durumu genel olarak iyi görünüyor."
            if locale == "tr"
            else "Mobile Sicherheitslage insgesamt gut."
        )
    return (
        "Kritik mobil bulgu tespit edilmedi; periyodik analiz önerilir."
        if locale == "tr"
        else "Keine kritischen mobilen Befunde; regelmäßige Analyse empfohlen."
    )
