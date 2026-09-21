import io
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from fastapi_app.main import app
from fastapi_app.core.database import Base, get_db, init_db
from fastapi_app.core.storage import init_storage

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

class TestSubscriptionAccessControl(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_db] = override_db
        Base.metadata.create_all(bind=engine)
        init_storage()

        # Seed initial subscription plans in the in-memory testing DB
        from fastapi_app.models.subscription import SubscriptionPlan
        db = TestingSession()
        plans = [
            SubscriptionPlan(name="Basic", price=0.0, duration_days=365, max_posts=1, max_images_per_post=1, max_likes=5, max_comments=5, description="Basic plan"),
            SubscriptionPlan(name="Premium", price=9.99, duration_days=30, max_posts=2, max_images_per_post=2, max_likes=20, max_comments=20, description="Premium plan"),
            SubscriptionPlan(name="Pro", price=29.99, duration_days=30, max_posts=-1, max_images_per_post=-1, max_likes=-1, max_comments=-1, description="Pro plan"),
        ]
        db.add_all(plans)
        db.commit()
        db.close()

        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        pass

    def test_01_get_plans(self):
        r = self.client.get("/subscriptions/plans")
        self.assertEqual(r.status_code, 200)
        plans = r.json()
        self.assertEqual(len(plans), 3)
        names = [p["name"] for p in plans]
        self.assertIn("Basic", names)
        self.assertIn("Premium", names)
        self.assertIn("Pro", names)

    def test_02_register_user_auto_basic_and_invoice(self):
        r = self.client.post("/auth/register", json={
            "username": "charlie",
            "email": "charlie@example.com",
            "password": "password123"
        })
        self.assertEqual(r.status_code, 201)
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Check /subscriptions/my-plan
        r_plan = self.client.get("/subscriptions/my-plan", headers=headers)
        self.assertEqual(r_plan.status_code, 200)
        data = r_plan.json()
        self.assertEqual(data["plan_name"], "Basic")
        self.assertEqual(data["max_posts"], 1)
        self.assertEqual(data["posts_count"], 0)
        self.assertTrue(data["can_create_post"])

        # Check /billing/history
        r_bill = self.client.get("/billing/history", headers=headers)
        self.assertEqual(r_bill.status_code, 200)
        history = r_bill.json()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["plan_name"], "Basic")
        self.assertTrue(history[0]["invoice_pdf_path"].startswith("/media/invoices/"))
        billing_id = history[0]["id"]

        # Check downloading invoice PDF
        r_pdf = self.client.get(f"/billing/invoices/{billing_id}", headers=headers)
        self.assertEqual(r_pdf.status_code, 200)
        self.assertEqual(r_pdf.headers["content-type"], "application/pdf")
        self.assertTrue(r_pdf.content.startswith(b"%PDF"))

    def test_03_basic_user_post_limit_enforcement(self):
        # Register user David
        r = self.client.post("/auth/register", json={
            "username": "david",
            "email": "david@example.com",
            "password": "password123"
        })
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Post #1 (allowed by Basic)
        r1 = self.client.post("/posts", data={"title": "David First Post", "content": "Hello World"}, headers=headers)
        self.assertEqual(r1.status_code, 201)

        # Post #2 (exceeds Basic limit of 1)
        r2 = self.client.post("/posts", data={"title": "David Second Post", "content": "Exceeding limit"}, headers=headers)
        self.assertEqual(r2.status_code, 403)
        self.assertIn("You’ve reached your plan limit. Kindly upgrade your plan to continue.", r2.json()["detail"])

    def test_04_basic_user_like_limit_enforcement(self):
        # Register creator Eva to make posts
        r_eva = self.client.post("/auth/register", json={
            "username": "eva",
            "email": "eva@example.com",
            "password": "password123"
        })
        token_eva = r_eva.json()["access_token"]
        headers_eva = {"Authorization": f"Bearer {token_eva}"}

        # Eva upgrades to Pro so she can create many posts for liking
        self.client.post("/subscriptions/subscribe", json={"plan_name": "Pro"}, headers=headers_eva)
        
        post_ids = []
        for i in range(7):
            r_p = self.client.post("/posts", data={"title": f"Eva Post #{i}", "content": f"Content #{i}"}, headers=headers_eva)
            self.assertEqual(r_p.status_code, 201)
            post_ids.append(r_p.json()["id"])

        # Register Basic user Frank
        r_frank = self.client.post("/auth/register", json={
            "username": "frank",
            "email": "frank@example.com",
            "password": "password123"
        })
        token_frank = r_frank.json()["access_token"]
        headers_frank = {"Authorization": f"Bearer {token_frank}"}

        # Frank likes 5 posts (Basic limit is 5)
        for i in range(5):
            r_like = self.client.post(f"/posts/{post_ids[i]}/like", headers=headers_frank)
            self.assertEqual(r_like.status_code, 200)
            self.assertTrue(r_like.json()["liked"])

        # Frank tries to like 6th post -> 403 Forbidden
        r_like6 = self.client.post(f"/posts/{post_ids[5]}/like", headers=headers_frank)
        self.assertEqual(r_like6.status_code, 403)
        self.assertIn("You’ve reached your plan limit. Kindly upgrade your plan to continue.", r_like6.json()["detail"])

    def test_05_basic_user_comment_limit_enforcement(self):
        # Register Basic user Grace
        r_grace = self.client.post("/auth/register", json={
            "username": "grace",
            "email": "grace@example.com",
            "password": "password123"
        })
        token_grace = r_grace.json()["access_token"]
        headers_grace = {"Authorization": f"Bearer {token_grace}"}

        # Post 1 post created by Grace
        r_p = self.client.post("/posts", data={"title": "Grace Post", "content": "Comments test"}, headers=headers_grace)
        post_id = r_p.json()["id"]

        # Grace adds 5 comments (Basic limit is 5)
        for i in range(5):
            r_comm = self.client.post(f"/posts/{post_id}/comments", json={"text": f"Comment #{i+1}"}, headers=headers_grace)
            self.assertEqual(r_comm.status_code, 201)

        # Grace tries to add 6th comment -> 403 Forbidden
        r_comm6 = self.client.post(f"/posts/{post_id}/comments", json={"text": "Comment #6 exceeding"}, headers=headers_grace)
        self.assertEqual(r_comm6.status_code, 403)
        self.assertIn("You’ve reached your plan limit. Kindly upgrade your plan to continue.", r_comm6.json()["detail"])

    def test_06_upgrade_flow_premium_and_pro(self):
        # Register user Henry
        r = self.client.post("/auth/register", json={
            "username": "henry",
            "email": "henry@example.com",
            "password": "password123"
        })
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create 1 post
        self.client.post("/posts", data={"title": "Henry Post 1", "content": "Basic post"}, headers=headers)

        # Exceeds limit
        r_blocked = self.client.post("/posts", data={"title": "Henry Post 2", "content": "Blocked"}, headers=headers)
        self.assertEqual(r_blocked.status_code, 403)

        # Upgrade to Premium ($9.99, max_posts=2)
        r_up = self.client.post("/subscriptions/subscribe", json={"plan_name": "Premium"}, headers=headers)
        self.assertEqual(r_up.status_code, 200)
        self.assertEqual(r_up.json()["plan"]["name"], "Premium")
        self.assertEqual(r_up.json()["billing"]["amount"], 9.99)
        self.assertTrue(r_up.json()["billing"]["invoice_pdf_path"].startswith("/media/invoices/"))

        # Now Post 2 succeeds
        r_p2 = self.client.post("/posts", data={"title": "Henry Post 2", "content": "Premium post"}, headers=headers)
        self.assertEqual(r_p2.status_code, 201)

        # Post 3 exceeds Premium limit (max_posts=2)
        r_p3_block = self.client.post("/posts", data={"title": "Henry Post 3", "content": "Blocked again"}, headers=headers)
        self.assertEqual(r_p3_block.status_code, 403)
        self.assertIn("You’ve reached your plan limit. Kindly upgrade your plan to continue.", r_p3_block.json()["detail"])

        # Upgrade to Pro (Unlimited)
        r_pro = self.client.post("/subscriptions/upgrade", json={"plan_name": "Pro"}, headers=headers)
        self.assertEqual(r_pro.status_code, 200)
        self.assertEqual(r_pro.json()["plan"]["name"], "Pro")

        # Now Post 3, 4, 5 succeed
        r_p3 = self.client.post("/posts", data={"title": "Henry Post 3", "content": "Pro post 3"}, headers=headers)
        self.assertEqual(r_p3.status_code, 201)
        r_p4 = self.client.post("/posts", data={"title": "Henry Post 4", "content": "Pro post 4"}, headers=headers)
        self.assertEqual(r_p4.status_code, 201)

if __name__ == "__main__":
    unittest.main()
