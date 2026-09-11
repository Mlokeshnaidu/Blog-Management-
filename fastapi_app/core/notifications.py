def send_email_notification(recipient_email: str, recipient_username: str, subject: str, message: str):
    """Trigger email notification in background."""
    print(f"\n--- [EMAIL NOTIFICATION] ---\nTo: {recipient_username} <{recipient_email}>\nSubject: {subject}\nMessage: {message}\n-----------------------------\n")
