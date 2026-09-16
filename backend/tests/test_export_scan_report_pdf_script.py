"""Export script must copy container PDF to a host path before SFTP."""

from pathlib import Path


def test_export_script_uses_docker_cp_and_validates_inputs() -> None:
    script = Path(__file__).resolve().parents[2] / "scripts" / "ssh-export-scan-report-pdf.cjs"
    text = script.read_text(encoding="utf-8")
    assert "docker cp siber-api:" in text
    assert "SIBER_EXPORT_OUT" in text
    assert "os.environ[\"SIBER_EXPORT_SCAN_ID\"]" in text
    assert "uuid.UUID(" in text
    assert "fastGet" in text
    assert "%PDF-" in text
    assert "rm -f" in text
    assert "dispatch_scan" not in text
    assert "Saved" in text
    assert "stage: generate-in-container" in text
    assert "stage: docker-cp-to-host" in text
    assert "conn.end()" in text
