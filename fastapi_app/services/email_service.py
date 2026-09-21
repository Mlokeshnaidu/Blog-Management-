import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from fastapi_app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    """Service to handle SMTP email transmission with in-memory auditing and fallback."""

    def __init__(self):
        self._sent_emails: List[Dict[str, Any]] = []

    def clear_sent_emails(self) -> None:
        """Clear the in-memory log of sent emails (useful for testing)."""
        self._sent_emails.clear()

    def get_sent_emails(self) -> List[Dict[str, Any]]:
        """Retrieve sent email history for auditing and verification."""
        return list(self._sent_emails)

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

        email_record = {
            "recipient_email": recipient_email,
            "recipient_name": recipient_name or recipient_email,
            "subject": subject,
            "body_text": body_text,
            "body_html": body_html,
            "sent_at": datetime.now().isoformat(),
            "status": "delivered"
        }

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
                email_record["status"] = "delivered"
                logger.info(f"Email successfully delivered to {recipient_email}")
            except Exception as e:
                email_record["status"] = f"failed ({str(e)})"
                logger.warning(f"SMTP dispatch failed gracefully: {e}")
        else:
            email_record["status"] = "delivered (mock/suppressed)"

        self._sent_emails.append(email_record)
        return email_record["status"] in ("delivered", "delivered (mock/suppressed)")

email_service = EmailService()
