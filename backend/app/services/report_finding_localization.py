"""Lokalisiert gespeicherte Findings für Scan-Reports (HTML/PDF/JSON)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.data.finding_catalog_de import SEVERITY_LABEL_DE
from app.data.finding_catalog_de import get_catalog_entry as get_catalog_entry_de
from app.i18n.report_strings import Locale
from app.models.finding import Finding
from app.services.finding_localization_service import extract_domain


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
        }
        base.update(overrides)
        return cls(**base)  # type: ignore[arg-type]


def _german_fallback(finding: Finding, domain: str) -> ReportFinding:
    sev_de = SEVERITY_LABEL_DE.get(finding.severity, finding.severity)
    if finding.source_tool == "nuclei" and finding.source_rule_id:
        risk_explanation = (
            f"Die Nuclei-Sicherheitsvorlage '{finding.source_rule_id}' meldet ein mögliches "
            f"Problem oder eine Fehlkonfiguration. Schweregrad: {sev_de}."
        )
        remediation_steps = [
            "Finding-Beschreibung lesen.",
            "Quellcode oder Server-Konfiguration für die betroffene Komponente prüfen.",
            "Fix in Staging anwenden und anschließend mit SIBER erneut scannen.",
        ]
        config_file_paths = [
            f"[Nginx] /etc/nginx/sites-available/{domain}",
            "[Apache] .htaccess im Document Root",
            "[Hosting-Panel] Domain-/SSL-Einstellungen (Plesk, cPanel, DirectAdmin usw.)",
            "[Anwendung] Relevanter Quellcode (Git/FTP)",
        ]
    else:
        risk_explanation = finding.risk_explanation or (
            f"{finding.title} — Schweregrad: {sev_de}."
        )
        remediation_steps = finding.remediation_steps or [
            "Technische Beschreibung prüfen.",
            "Server- oder Anwendungskonfiguration aktualisieren.",
        ]
        config_file_paths = finding.config_file_paths

    return ReportFinding.from_finding(
        finding,
        risk_explanation=risk_explanation,
        remediation_steps=remediation_steps,
        config_file_paths=config_file_paths,
    )


def localize_finding_for_report(finding: Finding, locale: Locale) -> ReportFinding:
    if locale != "de":
        return ReportFinding.from_finding(finding)

    rule_id = finding.correlation_key or finding.source_rule_id
    domain = extract_domain(finding.affected_url or "")
    if rule_id:
        entry = get_catalog_entry_de(rule_id, domain)
        if entry:
            return ReportFinding.from_finding(
                finding,
                title=entry["title_de"],
                description=entry["description_de"],
                risk_explanation=entry["risk_explanation_de"],
                remediation=entry["remediation_summary_de"],
                remediation_steps=entry["remediation_steps_de"],
                config_file_paths=entry["config_file_paths_de"],
                config_snippet=entry["config_snippet"],
            )

    return _german_fallback(finding, domain)


def localize_findings_for_report(findings: list[Finding], locale: Locale) -> list[ReportFinding]:
    return [localize_finding_for_report(finding, locale) for finding in findings]
