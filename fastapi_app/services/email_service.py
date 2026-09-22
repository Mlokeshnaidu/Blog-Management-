import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from fastapi_app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    """Service to handle SMTP email transmission."""

    def send_email_sync(
        self,
        recipient_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        recipient_name: Optional[str] = None
    ) -> bool:
        """Synchronously construct and transmit an email via configured SMTP server."""
        recip_display = f"{recipient_name} <{recipient_email}>" if recipient_name else recipient_email
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM}>"
        msg["To"] = recip_display

        # Attach Plain Text part
        msg.attach(MIMEText(body_text, "plain", "utf-8"))

        # Attach HTML part if provided
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))

        # Attempt SMTP transmission if not suppressed and credentials / host present
        if not settings.MAIL_SUPPRESS_SEND and settings.MAIL_SERVER:
            try:
                server = smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT, timeout=10)
                if settings.MAIL_STARTTLS:
                    server.starttls()
                if settings.MAIL_USERNAME and settings.MAIL_PASSWORD:
                    server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
                server.send_message(msg)
                server.quit()
                logger.info(f"Email successfully delivered to {recipient_email}")
                return True
            except Exception as e:
                logger.warning(f"SMTP dispatch failed gracefully: {e}")
                return False
        else:
            logger.info(f"Email suppressed/mock for {recipient_email}: {subject}")
            return True

email_service = EmailService()
