"""Root services alias module."""
from fastapi_app.services.email_service import email_service, EmailService
from fastapi_app.services.notification_service import notification_service, NotificationService

__all__ = ["email_service", "EmailService", "notification_service", "NotificationService"]
