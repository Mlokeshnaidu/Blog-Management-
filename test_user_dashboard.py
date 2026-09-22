import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from fastapi_app.main import app
from fastapi_app.core.database import Base, get_db
from fastapi_app.models.subscription import SubscriptionPlan
from fastapi_app.models.user import User
from fastapi_app.models.post import Post
from fastapi_app.models.like import Like
from fastapi_app.models.comment import Comment

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

class TestUserDashboardAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_db] = override_db
        Base.metadata.create_all(bind=engine)
        db = TestingSession()
        # Seed subscription plans
        plans = [
            SubscriptionPlan(name="Basic", price=0.0, duration_days=365, max_posts=10, max_images_per_post=2, max_likes=50, max_comments=50, description="Basic plan"),
            SubscriptionPlan(name="Premium", price=9.99, duration_days=30, max_posts=50, max_images_per_post=5, max_likes=200, max_comments=200, description="Premium plan"),
            SubscriptionPlan(name="Pro", price=29.99, duration_days=30, max_posts=-1, max_images_per_post=-1, max_likes=-1, max_comments=-1, description="Pro plan"),
        ]
        db.add_all(plans)
        db.commit()
        db.close()
        cls.client = TestClient(app)

    def test_01_unauthenticated_dashboard_rejected(self):
        """Unauthenticated requests to /user/dashboard should return 401 Unauthorized"""
        res = self.client.get("/user/dashboard")
        self.assertEqual(res.status_code, 401)
        self.assertIn("Not authenticated", res.json().get("detail", ""))

    def test_02_dashboard_html_view(self):
        """GET /dashboard and /user/dashboard/view should return interactive HTML page"""
        res = self.client.get("/dashboard")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Personal User Analytics & Activity Dashboard", res.text)
        self.assertIn("chart.js", res.text.lower())
        self.assertIn("barChartDistribution", res.text)
        self.assertIn("doughnutChartRatio", res.text)
        self.assertIn("lineChartTimeline", res.text)

        res2 = self.client.get("/user/dashboard/view")
        self.assertEqual(res2.status_code, 200)

    def test_03_post_views_tracking(self):
        """Viewing a post should dynamically increment its view counter"""
        # Register user
        reg_res = self.client.post("/auth/register", json={
            "username": "author_views_test",
            "email": "author_views@test.com",
            "password": "Password123!"
        })
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create post
        post_res = self.client.post("/posts", data={
            "title": "Post For Views Tracking",
            "content": "Testing view increments"
        }, headers=headers)
        self.assertEqual(post_res.status_code, 201)
        post_id = post_res.json()["id"]
        self.assertEqual(post_res.json().get("views", 0), 0)

        # Get post detail - should increment view to 1
        detail_res1 = self.client.get(f"/posts/{post_id}")
        self.assertEqual(detail_res1.status_code, 200)
        self.assertEqual(detail_res1.json()["views"], 1)

        # Get post detail again - should increment view to 2
        detail_res2 = self.client.get(f"/posts/{post_id}")
        self.assertEqual(detail_res2.status_code, 200)
        self.assertEqual(detail_res2.json()["views"], 2)

        # Explicit view endpoint
        view_endpoint_res = self.client.post(f"/posts/{post_id}/view")
        self.assertEqual(view_endpoint_res.status_code, 200)
        self.assertEqual(view_endpoint_res.json()["views"], 3)

    def test_04_user_dashboard_metrics_aggregation_and_isolation(self):
        """Verify calculations for user dashboard metrics and strict data isolation"""
        # 1. Register Author User
        r1 = self.client.post("/auth/register", json={
            "username": "analytics_author",
            "email": "analytics_author@test.com",
            "password": "Password123!"
        })
        t1 = r1.json()["access_token"]
        h1 = {"Authorization": f"Bearer {t1}"}

        # 2. Register Reader User
        r2 = self.client.post("/auth/register", json={
            "username": "analytics_reader",
            "email": "analytics_reader@test.com",
            "password": "Password123!"
        })
        t2 = r2.json()["access_token"]
        h2 = {"Authorization": f"Bearer {t2}"}

        # 3. Author creates 2 posts
        p1 = self.client.post("/posts", data={"title": "Analytics Post 1", "content": "Content 1"}, headers=h1).json()
        p2 = self.client.post("/posts", data={"title": "Analytics Post 2", "content": "Content 2"}, headers=h1).json()

        # Reader views posts (views = 1 on each)
        self.client.get(f"/posts/{p1['id']}")
        self.client.get(f"/posts/{p1['id']}")
        self.client.get(f"/posts/{p2['id']}")

        # Reader likes Post 1
        self.client.post(f"/posts/{p1['id']}/like", headers=h2)

        # Reader comments on Post 1 and Post 2
        self.client.post(f"/posts/{p1['id']}/comments", json={"text": "Great post 1!"}, headers=h2)
        self.client.post(f"/posts/{p2['id']}/comments", json={"text": "Insightful post 2!"}, headers=h2)

        # 4. Fetch Author's Dashboard
        dash_res = self.client.get("/user/dashboard", headers=h1)
        self.assertEqual(dash_res.status_code, 200)
        dash_data = dash_res.json()

        # Check Author Overview
        overview = dash_data["overview"]
        self.assertEqual(overview["total_posts"], 2)
        self.assertEqual(overview["total_post_views"], 3)  # 2 views on p1 + 1 view on p2
        self.assertEqual(overview["total_likes_received"], 1)
        self.assertEqual(overview["total_comments_received"], 2)
        self.assertEqual(overview["total_likes_given"], 0)
        self.assertEqual(overview["total_comments_made"], 0)
        self.assertGreater(overview["avg_likes_per_post"], 0)
        self.assertGreater(overview["avg_comments_per_post"], 0)
        self.assertGreater(overview["engagement_rate"], 0)

        # Check Author Post Analytics List
        self.assertEqual(len(dash_data["recent_posts"]), 2)
        self.assertEqual(len(dash_data["top_posts"]), 2)
        self.assertEqual(dash_data["distribution"]["likes_data"], [0, 1])
        self.assertEqual(dash_data["distribution"]["comments_data"], [1, 1])

        # 5. Check Reader's Dashboard (Strict User Isolation)
        reader_dash_res = self.client.get("/user/dashboard", headers=h2)
        self.assertEqual(reader_dash_res.status_code, 200)
        reader_data = reader_dash_res.json()

        r_overview = reader_data["overview"]
        self.assertEqual(r_overview["total_posts"], 0)
        self.assertEqual(r_overview["total_post_views"], 0)
        self.assertEqual(r_overview["total_likes_received"], 0)
        self.assertEqual(r_overview["total_comments_received"], 0)
        self.assertEqual(r_overview["total_likes_given"], 1)
        self.assertEqual(r_overview["total_comments_made"], 2)

    def test_05_dashboard_stats_and_timeframe(self):
        """Test /user/dashboard/stats and timeframe filtering"""
        reg_res = self.client.post("/auth/register", json={
            "username": "stats_user_test",
            "email": "stats_user@test.com",
            "password": "Password123!"
        })
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Stats endpoint
        stats_res = self.client.get("/user/dashboard/stats", headers=headers)
        self.assertEqual(stats_res.status_code, 200)
        self.assertEqual(stats_res.json()["total_posts"], 0)

        # Timeframe query
        dash_7d = self.client.get("/user/dashboard?timeframe=7d", headers=headers)
        self.assertEqual(dash_7d.status_code, 200)
        self.assertEqual(len(dash_7d.json()["timeline"]), 7)

        dash_30d = self.client.get("/user/dashboard?timeframe=30d", headers=headers)
        self.assertEqual(dash_30d.status_code, 200)
        self.assertEqual(len(dash_30d.json()["timeline"]), 30)

if __name__ == "__main__":
    unittest.main()
