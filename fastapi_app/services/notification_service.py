import html
from datetime import datetime
from typing import Optional
from fastapi import BackgroundTasks

from fastapi_app.services.email_service import email_service

class NotificationService:
    """Service to format and dispatch asynchronous email notifications for blog events."""

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

    def _render_html(
        self,
        recipient_name: str,
        post_title: str,
        actor_name: str,
        activity_type: str,
        timestamp_str: str,
        is_like: bool = False,
        extra_content: Optional[str] = None
    ) -> str:
        """Render sleek, modern HTML email template with dark-gradient styling."""
        safe_recipient = html.escape(recipient_name)
        safe_title = html.escape(post_title)
        safe_actor = html.escape(actor_name)
        safe_activity = html.escape(activity_type)
        safe_time = html.escape(timestamp_str)
        safe_extra = html.escape(extra_content) if extra_content else ""

        badge_color = "#e11d48" if is_like else "#2563eb"
        badge_icon = "❤️" if is_like else "💬"
        action_color = "#f43f5e" if is_like else "#3b82f6"

        extra_section = ""
        if safe_extra:
            extra_section = f"""
            <div style="margin-top: 15px; padding: 12px 16px; background: rgba(255,255,255,0.05); border-left: 3px solid {action_color}; border-radius: 4px; font-style: italic; color: #e2e8f0; font-size: 14px;">
                "{safe_extra}"
            </div>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_activity}</title>
</head>
<body style="margin: 0; padding: 30px 15px; background-color: #0b0f19; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f8fafc;">
    <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 580px; background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%); border-radius: 16px; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 20px 40px rgba(0,0,0,0.5); overflow: hidden;">
        <!-- Header -->
        <tr>
            <td style="padding: 28px 32px; background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); border-bottom: 1px solid rgba(255,255,255,0.08);">
                <table width="100%">
                    <tr>
                        <td>
                            <div style="display: inline-block; padding: 4px 10px; background: rgba(255,255,255,0.12); border-radius: 20px; font-size: 12px; font-weight: 600; color: #a5b4fc; text-transform: uppercase; letter-spacing: 0.5px;">
                                Blog Notification
                            </div>
                            <h1 style="margin: 10px 0 0 0; font-size: 20px; font-weight: 700; color: #ffffff;">
                                {badge_icon} {safe_activity}
                            </h1>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>

        <!-- Content -->
        <tr>
            <td style="padding: 32px;">
                <p style="margin: 0 0 20px 0; font-size: 15px; color: #94a3b8;">
                    Hello <strong style="color: #f8fafc;">{safe_recipient}</strong>,
                </p>
                <p style="margin: 0 0 24px 0; font-size: 15px; color: #cbd5e1; line-height: 1.5;">
                    Great news! There is new engagement on your blog post.
                </p>

                <!-- Post Card -->
                <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 20px; margin-bottom: 24px;">
                    <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; color: #64748b; margin-bottom: 6px; letter-spacing: 0.5px;">
                        Target Post
                    </div>
                    <div style="font-size: 17px; font-weight: 700; color: #38bdf8; margin-bottom: 16px;">
                        "{safe_title}"
                    </div>

                    <table width="100%" cellpadding="0" cellspacing="0">
                        <tr>
                            <td style="padding: 6px 0; font-size: 13px; color: #94a3b8; width: 100px;">User:</td>
                            <td style="padding: 6px 0; font-size: 13px; font-weight: 600; color: #f8fafc;">@{safe_actor}</td>
                        </tr>
                        <tr>
                            <td style="padding: 6px 0; font-size: 13px; color: #94a3b8;">Activity:</td>
                            <td style="padding: 6px 0; font-size: 13px; font-weight: 600; color: {badge_color};">
                                <span style="display: inline-block; padding: 2px 8px; background: rgba(255,255,255,0.06); border-radius: 6px;">
                                    {safe_activity}
                                </span>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 6px 0; font-size: 13px; color: #94a3b8;">Timestamp:</td>
                            <td style="padding: 6px 0; font-size: 13px; color: #cbd5e1;">{safe_time}</td>
                        </tr>
                    </table>
                    {extra_section}
                </div>

                <div style="text-align: center; margin-top: 28px;">
                    <a href="http://127.0.0.1:8000/admin" style="display: inline-block; background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-weight: 600; font-size: 14px; box-shadow: 0 4px 14px rgba(79, 70, 229, 0.4);">
                        View on Blog Platform &rarr;
                    </a>
                </div>
            </td>
        </tr>

        <!-- Footer -->
        <tr>
            <td style="padding: 20px 32px; background: rgba(0,0,0,0.2); border-top: 1px solid rgba(255,255,255,0.05); text-align: center; font-size: 12px; color: #64748b;">
                Blog Management API Notification Service &bull; Automated System
            </td>
        </tr>
    </table>
</body>
</html>
"""

    def _dispatch_email(
        self,
        recipient_email: str,
        recipient_name: str,
        subject: str,
        body_text: str,
        body_html: str,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> None:
        """Unified helper to dispatch notification asynchronously or synchronously."""
        if background_tasks is not None:
            background_tasks.add_task(
                email_service.send_email_sync,
                recipient_email=recipient_email,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                recipient_name=recipient_name
            )
        else:
            email_service.send_email_sync(
                recipient_email=recipient_email,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
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
        body_html = self._render_html(
            recipient_name=recipient_name,
            post_title=post_title,
            actor_name=actor_name,
            activity_type=activity_type,
            timestamp_str=timestamp_str,
            is_like=True
        )
        self._dispatch_email(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
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
        body_html = self._render_html(
            recipient_name=recipient_name,
            post_title=post_title,
            actor_name=actor_name,
            activity_type=activity_type,
            timestamp_str=timestamp_str,
            is_like=False,
            extra_content=comment_text
        )
        self._dispatch_email(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            background_tasks=background_tasks
        )

notification_service = NotificationService()
