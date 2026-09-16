"""SPF/DMARC parsing from TXT records (site profile consistency)."""

from app.scanners.site_intelligence import _parse_email_security


def test_spf_found_single_record() -> None:
    out = _parse_email_security(['v=spf1 include:_spf-eu.ionos.com ~all'])
    assert out["spf_status"] == "found"
    assert out["spf_present"] is True
    assert "ionos" in (out["spf_record"] or "")


def test_spf_found_quoted_chunks() -> None:
    out = _parse_email_security(['"v=spf1"', '" include:_spf-eu.ionos.com ~all"'])
    assert out["spf_status"] == "found"


def test_spf_invalid_multiple() -> None:
    out = _parse_email_security(
        ["v=spf1 include:a ~all", "v=spf1 include:b ~all"],
    )
    assert out["spf_status"] == "invalid_multiple"
    assert out["spf_present"] is False


def test_spf_not_found_without_spf_txt() -> None:
    out = _parse_email_security(["google-site-verification=abc", "v=DMARC1; p=none"])
    assert out["spf_status"] == "not_found"
    assert out["dmarc_status"] == "found"
