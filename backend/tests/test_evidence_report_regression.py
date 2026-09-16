"""Regression: correlated tool_evidence must survive into report text."""

from uuid import uuid4

from app.models.finding import Finding, FindingSeverity, FindingStatus
from app.services.finding_evidence import flatten_finding_evidence
from app.services.report_finding_enrichment import format_evidence_for_report


def _correlated_cert_evidence() -> dict:
    """Anonymized shape from production safe scan (nested tool_evidence)."""
    return {
        "correlation_key": "cert-expiring-soon",
        "source_count": 1,
        "sources": [{"tool": "tls_check", "rule_id": "cert-expiring-soon", "severity": "medium"}],
        "tool_evidence": {
            "tls_check": {
                "expires_at": "Oct 12 13:03:25 2026 GMT",
                "days_left": 27,
                "warning_threshold_days": 30,
            }
        },
    }


def _correlated_header_evidence() -> dict:
    return {
        "correlation_key": "server-disclosure",
        "source_count": 2,
        "sources": [
            {"tool": "passive_http", "rule_id": "server-disclosure", "severity": "info"},
            {"tool": "zap", "rule_id": "10096", "severity": "info"},
        ],
        "tool_evidence": {
            "passive_http": {
                "evidence_type": "http_header",
                "header_name": "Server",
                "header_value": "nginx",
                "server": "nginx",
            },
            "zap": {"matcher": "Server leaks version information"},
        },
    }


def test_flatten_tool_evidence_tls() -> None:
    flat = flatten_finding_evidence(_correlated_cert_evidence(), source_rule_id="cert-expiring-soon")
    assert flat.get("expires_at")
    assert flat.get("days_left") == 27


def test_report_shows_tls_fields() -> None:
    finding = Finding(
        id=uuid4(),
        organization_id=uuid4(),
        project_id=uuid4(),
        scan_job_id=uuid4(),
        source_tool="correlated",
        source_rule_id="cert-expiring-soon",
        correlation_key="cert-expiring-soon",
        title="TLS certificate expiring soon",
        severity=FindingSeverity.MEDIUM.value,
        status=FindingStatus.OPEN.value,
        affected_url="https://example.test/",
        evidence=_correlated_cert_evidence(),
    )
    text = format_evidence_for_report(finding, "tr")
    assert "27" in text
    assert "Oct 12" in text or "2026" in text
    assert "30" in text
    assert "Bu taramada ayrıntılı kanıt kaydedilmedi" not in text


def test_report_shows_server_from_tool_evidence() -> None:
    finding = Finding(
        id=uuid4(),
        organization_id=uuid4(),
        project_id=uuid4(),
        scan_job_id=uuid4(),
        source_tool="correlated",
        source_rule_id="server-disclosure",
        correlation_key="server-disclosure",
        title="Server version disclosure",
        severity=FindingSeverity.INFO.value,
        status=FindingStatus.OPEN.value,
        affected_url="https://example.test/",
        evidence=_correlated_header_evidence(),
    )
    text = format_evidence_for_report(finding, "tr")
    assert "nginx" in text
    assert "Bu taramada ayrıntılı kanıt kaydedilmedi" not in text


def _nested_x_powered_by() -> dict:
    return {
        "correlation_key": "x-powered-by-disclosure",
        "source_count": 2,
        "sources": [
            {"tool": "passive_http", "rule_id": "x-powered-by-disclosure", "severity": "low"},
            {"tool": "zap", "rule_id": "10037", "severity": "low"},
        ],
        "tool_evidence": {
            "passive_http": {
                "evidence_type": "http_header",
                "header_name": "X-Powered-By",
                "header_value": "Phusion Passenger(R), PleskLin",
                "x_powered_by": "Phusion Passenger(R), PleskLin",
            },
            "zap": {"plugin_id": "10037", "evidence": "Phusion Passenger(R), PleskLin"},
        },
    }


def test_nested_xpowered_read_by_formatter_and_remediation() -> None:
    from app.services.report_finding_localization import localize_finding_for_report
    from app.services.report_remediation_context import contextual_remediation

    finding = Finding(
        id=uuid4(),
        organization_id=uuid4(),
        project_id=uuid4(),
        scan_job_id=uuid4(),
        source_tool="correlated",
        source_rule_id="x-powered-by-disclosure",
        correlation_key="x-powered-by-disclosure",
        title="X-Powered-By disclosure",
        severity=FindingSeverity.LOW.value,
        status=FindingStatus.OPEN.value,
        affected_url="https://example.test/",
        evidence=_nested_x_powered_by(),
    )
    text = format_evidence_for_report(finding, "tr")
    assert "Phusion Passenger" in text
    _, steps, _ = contextual_remediation(finding, "tr")
    assert steps
    assert any("Phusion Passenger" in step for step in steps)
    assert not any(step.startswith("Gözlemlenen değer: —") for step in steps)
    assert not any(step.startswith("PHP:") for step in steps)
    localized = localize_finding_for_report(finding, "tr")
    assert localized.remediation_steps
    assert any("Phusion Passenger" in step for step in localized.remediation_steps)


def test_conflicting_header_values_are_not_silently_picked() -> None:
    evidence = {
        "tool_evidence": {
            "zap": {"header_name": "Server", "header_value": "nginx"},
            "passive_http": {"header_name": "Server", "header_value": "apache"},
        }
    }
    from app.services.finding_evidence import normalize_finding_evidence

    normalized = normalize_finding_evidence(evidence, source_tool="zap")
    assert "evidence_conflicts" in normalized
    assert "header_value" in normalized["evidence_conflicts"]


def test_cert_threshold_label_uses_scan_record() -> None:
    finding = Finding(
        id=uuid4(),
        organization_id=uuid4(),
        project_id=uuid4(),
        scan_job_id=uuid4(),
        source_tool="tls_check",
        source_rule_id="cert-expiring-soon",
        correlation_key="cert-expiring-soon",
        title="TLS certificate expiring soon",
        severity=FindingSeverity.MEDIUM.value,
        status=FindingStatus.OPEN.value,
        affected_url="https://example.test/",
        evidence=_correlated_cert_evidence(),
    )
    text = format_evidence_for_report(finding, "tr")
    assert "Taramada kaydedilen uyarı eşiği" in text
    assert "27" in text
    assert "varsayılan değil" in text


def test_missing_threshold_is_not_invented() -> None:
    finding = Finding(
        id=uuid4(),
        organization_id=uuid4(),
        project_id=uuid4(),
        scan_job_id=uuid4(),
        source_tool="tls_check",
        source_rule_id="cert-expiring-soon",
        title="TLS",
        severity=FindingSeverity.MEDIUM.value,
        status=FindingStatus.OPEN.value,
        evidence={"tool_evidence": {"tls_check": {"expires_at": "Oct 12 13:03:25 2026 GMT", "days_left": 27}}},
    )
    text = format_evidence_for_report(finding, "tr")
    assert "saklanmamış" in text
    assert "Uyarı eşiği (platform): 30" not in text
