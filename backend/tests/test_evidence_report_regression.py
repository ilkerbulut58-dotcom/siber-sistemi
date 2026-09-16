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
