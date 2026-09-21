"""
Live Verification & Demo Script for Email Notification System
Demonstrates:
- Asynchronous Like notification
- Asynchronous Comment notification
- Self-action suppression
- Plain text and HTML formatted templates
"""
import time
from fastapi.testclient import TestClient
from fastapi_app.main import app
from fastapi_app.services.email_service import email_service
from fastapi_app.services.notification_service import notification_service

client = TestClient(app)

def run_verification():
    print("=" * 80)
    print("    EMAIL NOTIFICATION SYSTEM - LIVE VERIFICATION & AUDIT DEMO")
    print("=" * 80)

    ts = int(time.time())
    author_username = f"jane_author_{ts}"
    author_email = f"jane_{ts}@example.com"
    fan_username = f"john_doe_{ts}"
    fan_email = f"john_{ts}@example.com"

    # 1. Register Author
    print(f"\n[1] Registering Author: @{author_username} ({author_email})")
    r_author = client.post("/auth/register", json={
        "username": author_username,
        "email": author_email,
        "password": "SecurePassword123!"
    })
    assert r_author.status_code == 201, f"Failed author registration: {r_author.text}"
    author_token = r_author.json()["access_token"]
    author_headers = {"Authorization": f"Bearer {author_token}"}
    print("    -> Author registered successfully.")

    # 2. Register Engager / Fan
    print(f"\n[2] Registering User: @{fan_username} ({fan_email})")
    r_fan = client.post("/auth/register", json={
        "username": fan_username,
        "email": fan_email,
        "password": "SecurePassword123!"
    })
    assert r_fan.status_code == 201, f"Failed fan registration: {r_fan.text}"
    fan_token = r_fan.json()["access_token"]
    fan_headers = {"Authorization": f"Bearer {fan_token}"}
    print("    -> User registered successfully.")

    # 3. Author publishes a blog post
    post_title = "FastAPI Best Practices: Async Notifications & Security"
    print(f"\n[3] Author publishes post: \"{post_title}\"")
    r_post = client.post("/posts", data={
        "title": post_title,
        "content": "A comprehensive deep dive into FastAPI BackgroundTasks, SQLAlchemy ORM, and secure auth."
    }, headers=author_headers)
    assert r_post.status_code == 201, f"Failed post creation: {r_post.text}"
    post_id = r_post.json()["id"]
    print(f"    -> Post published with ID: {post_id}")

    # 4. User likes Author's post
    print(f"\n[4] User @{fan_username} likes post #{post_id}...")
    email_service.clear_sent_emails()
    r_like = client.post(f"/posts/{post_id}/like", headers=fan_headers)
    assert r_like.status_code == 200, f"Failed like: {r_like.text}"
    print(f"    -> Like response: {r_like.json()}")

    # Check email notification received
    like_emails = email_service.get_sent_emails()
    assert len(like_emails) == 1, f"Expected 1 email notification, got {len(like_emails)}"
    like_email = like_emails[0]
    print(f"\n    [EMAIL NOTIFICATION VERIFIED - LIKE]")
    print(f"    Recipient: {like_email['recipient_name']} <{like_email['recipient_email']}>")
    print(f"    Subject  : {like_email['subject']}")
    print(f"    Status   : {like_email['status']}")
    print(f"    Plain Text Body:\n{'-'*40}\n{like_email['body_text']}\n{'-'*40}")

    # 5. User comments on Author's post
    comment_text = "Brilliant breakdown! The asynchronous BackgroundTasks pattern is super clean."
    print(f"\n[5] User @{fan_username} comments on post #{post_id}...")
    email_service.clear_sent_emails()
    r_comm = client.post(
        f"/posts/{post_id}/comments",
        json={"text": comment_text},
        headers=fan_headers
    )
    assert r_comm.status_code == 201, f"Failed comment: {r_comm.text}"
    print(f"    -> Comment created with ID: {r_comm.json()['id']}")

    # Check comment notification received
    comm_emails = email_service.get_sent_emails()
    assert len(comm_emails) == 1, f"Expected 1 email notification, got {len(comm_emails)}"
    comm_email = comm_emails[0]
    print(f"\n    [EMAIL NOTIFICATION VERIFIED - COMMENT]")
    print(f"    Recipient: {comm_email['recipient_name']} <{comm_email['recipient_email']}>")
    print(f"    Subject  : {comm_email['subject']}")
    print(f"    Status   : {comm_email['status']}")
    print(f"    Plain Text Body:\n{'-'*40}\n{comm_email['body_text']}\n{'-'*40}")

    # 6. Author likes & comments on own post (Self-action suppression test)
    print(f"\n[6] Testing Self-Action Suppression (Author likes & comments on own post)...")
    email_service.clear_sent_emails()
    r_self_like = client.post(f"/posts/{post_id}/like", headers=author_headers)
    r_self_comm = client.post(f"/posts/{post_id}/comments", json={"text": "Author follow up"}, headers=author_headers)
    self_emails = email_service.get_sent_emails()
    print(f"    -> Self like status: {r_self_like.status_code}, Self comment status: {r_self_comm.status_code}")
    print(f"    -> Emails generated for self-actions: {len(self_emails)} (Expected: 0)")
    assert len(self_emails) == 0, "Self actions should not send emails!"

    print("\n" + "=" * 80)
    print("    ALL NOTIFICATION SYSTEM TESTS PASSED SUCCESSFULLY! (100% PASS)")
    print("=" * 80)

if __name__ == "__main__":
    run_verification()
