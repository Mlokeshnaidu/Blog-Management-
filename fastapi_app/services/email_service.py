from fastapi_app.services.email_service import email_service

def send_email_notification(recipient_email: str, recipient_username: str, subject: str, message: str):
    """Trigger email notification in background using email service."""
    return email_service.send_email_sync(
        recipient_email=recipient_email,
        subject=subject,
        body_text=message,
        recipient_name=recipient_username
    )
