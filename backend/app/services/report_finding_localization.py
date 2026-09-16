"""Lokalisiert gespeicherte Findings für Scan-Reports (HTML/PDF/JSON)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.data.finding_catalog_de import SEVERITY_LABEL_DE
from app.data.finding_catalog_de import get_catalog_entry as get_catalog_entry_de
from app.data.finding_catalog_tr import SEVERITY_LABEL_TR
from app.data.finding_catalog_tr import get_catalog_entry as get_catalog_entry_tr
from app.i18n.report_strings import FINDING_STATUS_LABELS, Locale
from app.models.finding import Finding
from app.services.finding_localization_service import extract_domain
from app.services.report_catalog_keys import report_catalog_key
from app.services.report_finding_enrichment import (
    enrich_risk_explanation,
    format_evidence_for_report,
)
from app.services.report_remediation_context import contextual_remediation


@dataclass
class ReportFinding:
    id: UUID
    severity: str
    status: str
    title: str
    description: str | None
    risk_explanation: str | None
    affected_url: str | None
    remediation: str | None
    remediation_steps: list | None
    config_file_paths: list | None
    config_snippet: str | None
    source_tool: str | None
    source_rule_id: str | None
    risk_score: float | None
    ai_summary: str | None
    ai_remediation: str | None
    ai_confidence_label: str | None
    evidence_text: str | None = None
    confidence: str | None = None
    finding_type: str | None = None
    status_label: str | None = None
    technical_details: str | None = None

    @classmethod
    def from_finding(cls, finding: Finding, **overrides: object) -> ReportFinding:
        base = {
            "id": finding.id,
            "severity": finding.severity,
            "status": finding.status,
            "title": finding.title,
            "description": finding.description,
            "risk_explanation": finding.risk_explanation,
            "affected_url": finding.affected_url,
            "remediation": finding.remediation,
            "remediation_steps": finding.remediation_steps,
            "config_file_paths": finding.config_file_paths,
            "config_snippet": finding.config_snippet,
            "source_tool": finding.source_tool,
            "source_rule_id": finding.source_rule_id,
            "risk_score": finding.risk_score,
            "ai_summary": finding.ai_summary,
            "ai_remediation": finding.ai_remediation,
            "ai_confidence_label": finding.ai_confidence_label,
            "confidence": finding.confidence,
            "finding_type": (finding.evidence or {}).get("finding_type") if finding.evidence else None,
            "status_label": None,
            "technical_details": None,
        }
        base.update(overrides)
        return cls(**base)  # type: ignore[arg-type]


def _technical_details(finding: Finding, locale: Locale) -> str:
    heading = "Özgün motor çıktısı" if locale == "tr" else "Originalausgabe der Scan-Engine"
    title_label = "Başlık" if locale == "tr" else "Titel"
    description_label = "Açıklama" if locale == "tr" else "Beschreibung"
    remediation_label = "Çözüm" if locale == "tr" else "Lösung"
    rows = [
        heading,
        f"{title_label}: {finding.title or '—'}",
        f"{description_label}: {finding.description or '—'}",
    ]
    if finding.remediation:
        rows.append(f"{remediation_label}: {finding.remediation}")
    return "\n".join(rows)


def _localized_unknown_fallback(finding: Finding, locale: Locale) -> ReportFinding:
    """Localized wrapper for rules absent from the catalog; engine text stays technical."""
    tool = finding.source_tool or "scanner"
    rule = finding.source_rule_id or finding.correlation_key or "—"
    if locale == "de":
        severity = SEVERITY_LABEL_DE.get(finding.severity, finding.severity)
        return ReportFinding.from_finding(
            finding,
            title=f"Nicht katalogisierter Sicherheitsbefund ({tool}: {rule})",
            description=(
                "Die Scan-Engine hat einen Befund gemeldet, für den noch keine geprüfte "
                "deutsche Fachübersetzung im Katalog vorhanden ist."
            ),
            risk_explanation=(
                f"Der Befund muss technisch geprüft werden. Gemeldeter Schweregrad: {severity}. "
                "Die Originalmeldung ist getrennt im technischen Anhang aufgeführt."
            ),
            remediation=(
                "Originalnachweis und betroffene Komponente prüfen; eine Änderung erst nach "
                "technischer Bestätigung in einer Testumgebung umsetzen."
            ),
            remediation_steps=[
                "Regel-ID, betroffene URL und unveränderten Nachweis gemeinsam prüfen.",
                "Hersteller- oder Engine-Dokumentation zur angegebenen Regel-ID heranziehen.",
                "Korrektur zuerst in Staging testen und danach erneut scannen.",
            ],
            config_file_paths=finding.config_file_paths,
            config_snippet=finding.config_snippet,
            technical_details=_technical_details(finding, locale),
            ai_summary=None,
            ai_remediation=None,
        )

    severity = SEVERITY_LABEL_TR.get(finding.severity, finding.severity)
    return ReportFinding.from_finding(
        finding,
        title=f"Katalogda bulunmayan güvenlik bulgusu ({tool}: {rule})",
        description=(
            "Tarama motoru, doğrulanmış Türkçe teknik çevirisi henüz katalogda bulunmayan "
            "bir bulgu bildirdi."
        ),
        risk_explanation=(
            f"Bulgu teknik olarak incelenmelidir. Bildirilen önem derecesi: {severity}. "
            "Özgün motor metni teknik ekte ayrı olarak gösterilmiştir."
        ),
        remediation=(
            "Özgün kanıtı ve etkilenen bileşeni inceleyin; teknik doğrulama yapılmadan "
            "üretim ortamında değişiklik uygulamayın."
        ),
        remediation_steps=[
            "Kural kimliği, etkilenen URL ve değiştirilmemiş kanıtı birlikte inceleyin.",
            "Belirtilen kural kimliği için üretici veya tarama motoru belgelerine bakın.",
            "Düzeltmeyi önce test ortamında uygulayın ve ardından yeniden tarayın.",
        ],
        config_file_paths=finding.config_file_paths,
        config_snippet=finding.config_snippet,
        technical_details=_technical_details(finding, locale),
        ai_summary=None,
        ai_remediation=None,
    )


def localize_finding_for_report(finding: Finding, locale: Locale) -> ReportFinding:
    evidence_text = format_evidence_for_report(finding, locale)
    risk = enrich_risk_explanation(finding, locale)
    rem_override, steps_override, snippet_override = contextual_remediation(finding, locale)

    rule_id = report_catalog_key(finding) or finding.correlation_key or finding.source_rule_id
    domain = extract_domain(finding.affected_url or "")
    if rule_id:
        entry = get_catalog_entry_de(rule_id, domain) if locale == "de" else get_catalog_entry_tr(rule_id, domain)
        if entry:
            prefix = "de" if locale == "de" else "tr"
            use_override = rem_override is not None
            catalog_risk = entry[f"risk_explanation_{prefix}"]
            catalog_key = report_catalog_key(finding)
            if catalog_key.startswith("generic.csp") or catalog_key.startswith("generic.re-examine"):
                risk_text = risk or catalog_risk
            else:
                risk_text = catalog_risk
            return ReportFinding.from_finding(
                finding,
                title=entry[f"title_{prefix}"],
                description=entry[f"description_{prefix}"],
                risk_explanation=risk_text,
                remediation=rem_override if use_override else entry[f"remediation_summary_{prefix}"],
                remediation_steps=steps_override if use_override else entry[f"remediation_steps_{prefix}"],
                config_file_paths=entry[f"config_file_paths_{prefix}"],
                config_snippet=snippet_override if use_override else entry["config_snippet"],
                evidence_text=evidence_text,
                source_rule_id=finding.source_rule_id,
                status_label=FINDING_STATUS_LABELS[locale].get(finding.status, finding.status),
                ai_summary=None,
                ai_remediation=None,
            )

    fb = _localized_unknown_fallback(finding, locale)
    return ReportFinding.from_finding(
        finding,
        title=fb.title,
        description=fb.description,
        risk_explanation=fb.risk_explanation,
        remediation=fb.remediation,
        remediation_steps=fb.remediation_steps,
        config_file_paths=fb.config_file_paths,
        config_snippet=fb.config_snippet,
        evidence_text=evidence_text,
        status_label=FINDING_STATUS_LABELS[locale].get(finding.status, finding.status),
        technical_details=fb.technical_details,
        ai_summary=None,
        ai_remediation=None,
    )


def localize_findings_for_report(findings: list[Finding], locale: Locale) -> list[ReportFinding]:
    return [localize_finding_for_report(finding, locale) for finding in findings]
