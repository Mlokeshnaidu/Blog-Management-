import unittest
from datetime import datetime
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from fastapi_app.main import app
from fastapi_app.core.database import Base, get_db
from fastapi_app.services.email_service import email_service
from fastapi_app.services.notification_service import notification_service
from fastapi_app.models.subscription import SubscriptionPlan

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_db

class TestEmailNotificationSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_db] = override_db
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        Base.metadata.create_all(bind=engine)
        db = TestingSession()
        from fastapi_app.models.subscription import SubscriptionPlan
        if not db.query(SubscriptionPlan).filter(SubscriptionPlan.name == "Basic").first():
            plans = [
                SubscriptionPlan(name="Basic", price=0.0, duration_days=365, max_posts=10, max_images_per_post=2, max_likes=50, max_comments=50, description="Basic plan"),
                SubscriptionPlan(name="Pro", price=29.99, duration_days=30, max_posts=-1, max_images_per_post=-1, max_likes=-1, max_comments=-1, description="Pro plan"),
            ]
            db.add_all(plans)
            db.commit()
        db.close()
        email_service.clear_sent_emails()

    def test_01_direct_notification_formatting(self):
        fixed_time = datetime(2026, 3, 4, 11, 20)
        formatted_time = notification_service.format_timestamp(fixed_time)
        self.assertEqual(formatted_time, "2026-03-04 11:20 AM")

        # Plain text verification
        text = notification_service._render_plain_text(
            recipient_name="Alice",
            post_title="FastAPI Best Practices",
            actor_name="John Doe",
            activity_type="Commented on your post",
            timestamp_str=formatted_time,
            extra_content="Great post!"
        )
        self.assertIn('Post: "FastAPI Best Practices"', text)
        self.assertIn("User: John Doe", text)
        self.assertIn("Activity: Commented on your post", text)
        self.assertIn("Time: 2026-03-04 11:20 AM", text)
        self.assertIn('Comment Details: "Great post!"', text)

        # HTML verification
        html = notification_service._render_html(
            recipient_name="Alice",
            post_title="FastAPI Best Practices",
            actor_name="John Doe",
            activity_type="Commented on your post",
            timestamp_str=formatted_time,
            is_like=False,
            extra_content="Great post!"
        )
        self.assertIn("FastAPI Best Practices", html)
        self.assertIn("@John Doe", html)
        self.assertIn("2026-03-04 11:20 AM", html)
        self.assertIn("Great post!", html)

    def test_02_comment_email_notification_trigger(self):
        # Register author (Alice)
        r_alice = self.client.post("/auth/register", json={
            "username": "author_alice",
            "email": "alice_author@example.com",
            "password": "Password123!"
        })
        self.assertEqual(r_alice.status_code, 201)
        token_alice = r_alice.json()["access_token"]
        headers_alice = {"Authorization": f"Bearer {token_alice}"}

        # Register commenter (Bob)
        r_bob = self.client.post("/auth/register", json={
            "username": "commenter_bob",
            "email": "bob_commenter@example.com",
            "password": "Password123!"
        })
        self.assertEqual(r_bob.status_code, 201)
        token_bob = r_bob.json()["access_token"]
        headers_bob = {"Authorization": f"Bearer {token_bob}"}

        # Alice creates a post
        r_post = self.client.post("/posts", data={
            "title": "Scalable Email Notifications in FastAPI",
            "content": "Designing clean event-driven email notifications using BackgroundTasks."
        }, headers=headers_alice)
        self.assertEqual(r_post.status_code, 201)
        post_id = r_post.json()["id"]

        email_service.clear_sent_emails()

        # Bob comments on Alice's post
        r_comment = self.client.post(
            f"/posts/{post_id}/comments",
            json={"text": "Incredible architecture and clean implementation!"},
            headers=headers_bob
        )
        self.assertEqual(r_comment.status_code, 201)

        # Verify email was dispatched to Alice
        sent = email_service.get_sent_emails()
        self.assertEqual(len(sent), 1)
        email = sent[0]
        self.assertEqual(email["recipient_email"], "alice_author@example.com")
        self.assertEqual(email["recipient_name"], "author_alice")
        self.assertIn('New Comment on: "Scalable Email Notifications in FastAPI"', email["subject"])
        self.assertIn('Post: "Scalable Email Notifications in FastAPI"', email["body_text"])
        self.assertIn("User: commenter_bob", email["body_text"])
        self.assertIn("Activity: Commented on your post", email["body_text"])
        self.assertIn("Time:", email["body_text"])
        self.assertIn("Incredible architecture and clean implementation!", email["body_text"])

    def test_03_like_email_notification_trigger(self):
        # Register author (Charlie) and fan (Diana)
        r_charlie = self.client.post("/auth/register", json={
            "username": "charlie_writer",
            "email": "charlie@example.com",
            "password": "Password123!"
        })
        token_charlie = r_charlie.json()["access_token"]
        headers_charlie = {"Authorization": f"Bearer {token_charlie}"}

        r_diana = self.client.post("/auth/register", json={
            "username": "diana_fan",
            "email": "diana@example.com",
            "password": "Password123!"
        })
        token_diana = r_diana.json()["access_token"]
        headers_diana = {"Authorization": f"Bearer {token_diana}"}

        # Charlie creates a post
        r_post = self.client.post("/posts", data={
            "title": "Modern Microservices with Docker",
            "content": "A deep dive into containerization."
        }, headers=headers_charlie)
        self.assertEqual(r_post.status_code, 201)
        post_id = r_post.json()["id"]

        email_service.clear_sent_emails()

        # Diana likes Charlie's post
        r_like = self.client.post(f"/posts/{post_id}/like", headers=headers_diana)
        self.assertEqual(r_like.status_code, 200)
        self.assertTrue(r_like.json()["liked"])

        # Verify email was dispatched to Charlie
        sent = email_service.get_sent_emails()
        self.assertEqual(len(sent), 1)
        email = sent[0]
        self.assertEqual(email["recipient_email"], "charlie@example.com")
        self.assertEqual(email["recipient_name"], "charlie_writer")
        self.assertIn('New Like on: "Modern Microservices with Docker"', email["subject"])
        self.assertIn('Post: "Modern Microservices with Docker"', email["body_text"])
        self.assertIn("User: diana_fan", email["body_text"])
        self.assertIn("Activity: Liked your post", email["body_text"])
        self.assertIn("Time:", email["body_text"])

    def test_04_author_self_action_suppression(self):
        # Register author (Eve)
        r_eve = self.client.post("/auth/register", json={
            "username": "eve_author",
            "email": "eve@example.com",
            "password": "Password123!"
        })
        token_eve = r_eve.json()["access_token"]
        headers_eve = {"Authorization": f"Bearer {token_eve}"}

        # Eve creates a post
        r_post = self.client.post("/posts", data={
            "title": "Self Testing Guidelines",
            "content": "Testing edge cases."
        }, headers=headers_eve)
        post_id = r_post.json()["id"]

        email_service.clear_sent_emails()

        # Eve likes her own post -> No email should be sent
        r_like = self.client.post(f"/posts/{post_id}/like", headers=headers_eve)
        self.assertEqual(r_like.status_code, 200)
        self.assertEqual(len(email_service.get_sent_emails()), 0)

        # Eve comments on her own post -> No email should be sent
        r_comment = self.client.post(
            f"/posts/{post_id}/comments",
            json={"text": "Author follow-up note."},
            headers=headers_eve
        )
        self.assertEqual(r_comment.status_code, 201)
        self.assertEqual(len(email_service.get_sent_emails()), 0)

    def test_05_graceful_error_handling_on_smtp_failure(self):
        # Register user Frank and George
        r_frank = self.client.post("/auth/register", json={
            "username": "frank_author",
            "email": "frank@example.com",
            "password": "Password123!"
        })
        token_frank = r_frank.json()["access_token"]
        headers_frank = {"Authorization": f"Bearer {token_frank}"}

        r_george = self.client.post("/auth/register", json={
            "username": "george_user",
            "email": "george@example.com",
            "password": "Password123!"
        })
        token_george = r_george.json()["access_token"]
        headers_george = {"Authorization": f"Bearer {token_george}"}

        # Frank creates post
        r_post = self.client.post("/posts", data={
            "title": "Fault Tolerance Post",
            "content": "Resilience in production systems."
        }, headers=headers_frank)
        post_id = r_post.json()["id"]

        # Mock smtplib to raise an exception simulating network outage or invalid SMTP host
        with patch("smtplib.SMTP", side_effect=ConnectionRefusedError("SMTP server unreachable")):
            # George comments - API should still return 201 and not crash
            r_comm = self.client.post(
                f"/posts/{post_id}/comments",
                json={"text": "Testing fault tolerance!"},
                headers=headers_george
            )
            self.assertEqual(r_comm.status_code, 201)

            # George likes - API should still return 200 and not crash
            r_like = self.client.post(f"/posts/{post_id}/like", headers=headers_george)
            self.assertEqual(r_like.status_code, 200)

if __name__ == "__main__":
    unittest.main()
