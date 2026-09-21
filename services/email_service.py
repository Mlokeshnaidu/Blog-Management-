"""Root email_service alias."""
from fastapi_app.services.email_service import email_service, EmailService

__all__ = ["email_service", "EmailService"]
