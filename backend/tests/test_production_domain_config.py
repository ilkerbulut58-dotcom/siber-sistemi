"""Production must not allow DNS verification bypass via env flags."""

import pytest

from app.core.config import Settings, get_settings


def test_production_rejects_skip_domain_flags() -> None:
    with pytest.raises(ValueError, match="Production cannot start"):
        Settings(
            environment="production",
            skip_domain_verification=True,
            pilot_relax_domain_verification=False,
        )


def test_production_rejects_pilot_relax_flag() -> None:
    with pytest.raises(ValueError, match="Production cannot start"):
        Settings(
            environment="production",
            skip_domain_verification=False,
            pilot_relax_domain_verification=True,
        )


def test_staging_still_enforces_verification_when_skip_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("SKIP_DOMAIN_VERIFICATION", "true")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.domain_verification_enforced() is True
    get_settings.cache_clear()
