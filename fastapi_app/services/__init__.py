"""Services module for external integrations and background workers."""
from fastapi_app.services.email_service import email_service
from fastapi_app.services.notification_service import notification_service

__all__ = ["email_service", "notification_service"]
