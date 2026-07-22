"""Tests for sensitive data scanner."""

from __future__ import annotations

from app.scanners import sensitive_data as mod
from app.scanners.sensitive_data import _luhn_valid, scan_sensitive_data


def test_luhn_validates_known_test_card() -> None:
    assert _luhn_valid("4111111111111111") is True
    assert _luhn_valid("1234567890123456") is False


def test_turkish_iban_pattern() -> None:
    pattern = next(p for rid, _, p, _ in mod.PATTERNS if rid == "turkish-iban")
    assert pattern.search("TR330006100519786457841326")


async def test_scan_sensitive_data_empty_url() -> None:
    findings = await scan_sensitive_data("not-a-url")
    assert findings == []
