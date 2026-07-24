import pytest

from app.services.email_service import EmailService


@pytest.mark.asyncio
async def test_send_skips_when_smtp_disabled() -> None:
    service = EmailService()
    if service.is_configured:
        pytest.skip("SMTP configured in environment")
    ok = await service.send(to="a@b.com", subject="Hi", text_body="Test")
    assert ok is False
