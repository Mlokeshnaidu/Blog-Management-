from datetime import datetime
from typing import Optional
from fastapi import BackgroundTasks

from fastapi_app.services.email_service import email_service

class NotificationService:
    """Service to format and dispatch email notifications for blog events."""

    def format_timestamp(self, dt: Optional[datetime] = None) -> str:
        """Format timestamp in the standard requirement format: 2026-03-04 11:20 AM."""
        current = dt or datetime.now()
        return current.strftime("%Y-%m-%d %I:%M %p")

    def _render_plain_text(
        self,
        recipient_name: str,
        post_title: str,
        actor_name: str,
        activity_type: str,
        timestamp_str: str,
        extra_content: Optional[str] = None
    ) -> str:
        """Render plain text email according to task specification."""
        text = (
            f"Hi {recipient_name},\n\n"
            f"Someone interacted with your post on Blog Management!\n\n"
            f"Post: \"{post_title}\"\n"
            f"User: {actor_name}\n"
            f"Activity: {activity_type}\n"
            f"Time: {timestamp_str}\n"
        )
        if extra_content:
            text += f"\nComment Details: \"{extra_content}\"\n"
        text += "\nBest regards,\nBlog Management System Team"
        return text

    def _dispatch_email(
        self,
        recipient_email: str,
        recipient_name: str,
        subject: str,
        body_text: str,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> None:
        """Unified helper to dispatch notification asynchronously or synchronously."""
        if background_tasks is not None:
            background_tasks.add_task(
                email_service.send_email_sync,
                recipient_email=recipient_email,
                subject=subject,
                body_text=body_text,
                recipient_name=recipient_name
            )
        else:
            email_service.send_email_sync(
                recipient_email=recipient_email,
                subject=subject,
                body_text=body_text,
                recipient_name=recipient_name
            )

    def send_like_notification(
        self,
        post_title: str,
        recipient_email: str,
        recipient_name: str,
        actor_name: str,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> None:
        """Trigger asynchronous email notification when someone likes a post."""
        timestamp_str = self.format_timestamp()
        activity_type = "Liked your post"
        subject = f'New Like on: "{post_title}"'
        body_text = self._render_plain_text(
            recipient_name=recipient_name,
            post_title=post_title,
            actor_name=actor_name,
            activity_type=activity_type,
            timestamp_str=timestamp_str
        )
        self._dispatch_email(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            body_text=body_text,
            background_tasks=background_tasks
        )

    def send_comment_notification(
        self,
        post_title: str,
        recipient_email: str,
        recipient_name: str,
        actor_name: str,
        comment_text: str,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> None:
        """Trigger asynchronous email notification when someone comments on a post."""
        timestamp_str = self.format_timestamp()
        activity_type = "Commented on your post"
        subject = f'New Comment on: "{post_title}"'
        body_text = self._render_plain_text(
            recipient_name=recipient_name,
            post_title=post_title,
            actor_name=actor_name,
            activity_type=activity_type,
            timestamp_str=timestamp_str,
            extra_content=comment_text
        )
        self._dispatch_email(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            body_text=body_text,
            background_tasks=background_tasks
        )

notification_service = NotificationService()
