"""Outbound transactional email via SMTP (Plesk Postfix)."""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def is_configured(self) -> bool:
        s = self.settings
        return bool(s.smtp_enabled and s.smtp_host and s.email_from)

    def _send_sync(self, *, to: str, subject: str, text_body: str, html_body: str | None = None) -> None:
        settings = self.settings
        msg = EmailMessage()
        msg["From"] = settings.email_from
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(text_body)
        if html_body:
            msg.add_alternative(html_body, subtype="html")

        use_tls = settings.smtp_use_tls
        port = settings.smtp_port
        host = settings.smtp_host

        if use_tls and port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=settings.smtp_timeout_seconds) as smtp:
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(msg)
            return

        with smtplib.SMTP(host, port, timeout=settings.smtp_timeout_seconds) as smtp:
            if use_tls:
                smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)

    async def send(self, *, to: str, subject: str, text_body: str, html_body: str | None = None) -> bool:
        if not self.is_configured:
            logger.info("email.skipped_unconfigured", extra={"to": to, "subject": subject})
            return False
        try:
            await asyncio.to_thread(
                self._send_sync,
                to=to,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
            )
            logger.info("email.sent", extra={"to": to, "subject": subject})
            return True
        except Exception:
            logger.exception("email.send_failed", extra={"to": to, "subject": subject})
            return False

    def _frontend_base(self) -> str:
        return self.settings.frontend_public_url.rstrip("/")

    async def send_verification_email(self, to: str, token: str) -> bool:
        link = f"{self._frontend_base()}/verify-email?token={token}"
        subject = "SIBER — E-posta doğrulama / E-Mail-Verifizierung"
        text = (
            "SIBER hesabınızı doğrulamak için bağlantıyı açın:\n"
            f"{link}\n\n"
            "Link 24 saat geçerlidir.\n\n"
            "---\n"
            "Bitte öffnen Sie den Link zur E-Mail-Verifizierung:\n"
            f"{link}\n"
        )
        html = (
            f"<p>SIBER hesabınızı doğrulamak için:</p>"
            f'<p><a href="{link}">E-postayı doğrula</a></p>'
            f"<p><small>Link 24 saat geçerlidir.</small></p>"
            f"<hr><p>Bitte klicken Sie zur Verifizierung:</p>"
            f'<p><a href="{link}">E-Mail bestätigen</a></p>'
        )
        return await self.send(to=to, subject=subject, text_body=text, html_body=html)

    async def send_password_reset_email(self, to: str, token: str) -> bool:
        link = f"{self._frontend_base()}/reset-password?token={token}"
        subject = "SIBER — Şifre sıfırlama / Passwort zurücksetzen"
        text = (
            "Şifrenizi sıfırlamak için:\n"
            f"{link}\n\n"
            "Link 1 saat geçerlidir. Talep etmediyseniz bu e-postayı yok sayın.\n\n"
            "---\n"
            "Passwort zurücksetzen:\n"
            f"{link}\n"
        )
        html = (
            f'<p><a href="{link}">Şifreyi sıfırla / Passwort zurücksetzen</a></p>'
            f"<p><small>Link 1 saat geçerlidir.</small></p>"
        )
        return await self.send(to=to, subject=subject, text_body=text, html_body=html)
