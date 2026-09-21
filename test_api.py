import io
import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from fastapi_app.main import app
from fastapi_app.core.database import Base, get_db

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

class TestBlogAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_db] = override_db
        Base.metadata.create_all(bind=engine)
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

    def test_00_root_and_docs(self):
        # Test Root endpoint
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("docs", r.json())

        # Test Swagger UI endpoint
        r = self.client.get("/docs")
        self.assertEqual(r.status_code, 200)

    def test_01_auth_flow_and_validation(self):
        # 1. Validation error: invalid email format
        r = self.client.post("/auth/register", json={"username": "invalid_user", "email": "not-an-email", "password": "123"})
        self.assertEqual(r.status_code, 422)

        # 2. Register Alice
        r = self.client.post("/auth/register", json={"username": "alice", "email": "alice@mail.com", "password": "password123"})
        self.assertEqual(r.status_code, 201)
        data = r.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["user"]["username"], "alice")

        # 3. Duplicate registration error (username)
        r = self.client.post("/auth/register", json={"username": "alice", "email": "alice2@mail.com", "password": "password123"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("Username already registered", r.json()["detail"])

        # 4. Duplicate registration error (email)
        r = self.client.post("/auth/register", json={"username": "alice2", "email": "alice@mail.com", "password": "password123"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("Email already registered", r.json()["detail"])

        # 5. Register Bob
        r = self.client.post("/auth/register", json={"username": "bob", "email": "bob@mail.com", "password": "password123"})
        self.assertEqual(r.status_code, 201)

        # 6. Login successfully with username
        r = self.client.post("/auth/login", json={"username": "alice", "password": "password123"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("access_token", r.json())
        token = r.json()["access_token"]

        # 7. Login with email
        r = self.client.post("/auth/login", json={"username": "alice@mail.com", "password": "password123"})
        self.assertEqual(r.status_code, 200)

        # 8. Login failed with invalid password
        r = self.client.post("/auth/login", json={"username": "alice", "password": "wrongpassword"})
        self.assertEqual(r.status_code, 401)

        # 9. Test /auth/me
        r = self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["username"], "alice")

        # 10. Test /auth/me unauthenticated
        r = self.client.get("/auth/me")
        self.assertEqual(r.status_code, 401)

    def test_02_posts_crud_image_upload_and_ownership(self):
        # Login tokens
        r_a = self.client.post("/auth/login", json={"username": "alice", "password": "password123"})
        headers_a = {"Authorization": f"Bearer {r_a.json()['access_token']}"}

        r_b = self.client.post("/auth/login", json={"username": "bob", "password": "password123"})
        headers_b = {"Authorization": f"Bearer {r_b.json()['access_token']}"}

        # 1. Reject invalid file format
        fake_txt = io.BytesIO(b"not an image file")
        r = self.client.post(
            "/posts/create",
            data={"title": "Invalid File Post", "content": "Checking extension filter."},
            files={"image": ("malicious.exe", fake_txt, "application/x-msdownload")},
            headers=headers_a
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("Invalid image format", r.json()["detail"])

        # 2. Create Post with Image Upload via /posts/create
        fake_image = io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRfake_png_binary_data")
        r = self.client.post(
            "/posts/create",
            data={"title": "FastAPI Guide with Cover", "content": "Learn FastAPI easily with visuals."},
            files={"image": ("cover.png", fake_image, "image/png")},
            headers=headers_a
        )
        self.assertEqual(r.status_code, 201)
        post_data = r.json()
        post_id = post_data["id"]
        self.assertIsNotNone(post_data["image"])
        self.assertTrue(post_data["image"].startswith("/media/posts/"))
        image_url = post_data["image"]

        # 3. Verify static file serving for uploaded image
        r_static = self.client.get(image_url)
        self.assertEqual(r_static.status_code, 200)

        # 4a. Basic plan limit check: Alice tries to create a 2nd post -> 403
        r_blocked = self.client.post(
            "/posts",
            data={"title": "FastAPI Async Insights", "content": "Deep dive into async await in Python."},
            headers=headers_a
        )
        self.assertEqual(r_blocked.status_code, 403)
        self.assertIn("You’ve reached your plan limit. Kindly upgrade your plan to continue.", r_blocked.json()["detail"])

        # 4b. Alice upgrades to Pro plan to get unlimited posts
        r_upgrade = self.client.post("/subscriptions/subscribe", json={"plan_name": "Pro"}, headers=headers_a)
        self.assertEqual(r_upgrade.status_code, 200)

        # 4c. Create Post without Image now succeeds
        r2 = self.client.post(
            "/posts",
            data={"title": "FastAPI Async Insights", "content": "Deep dive into async await in Python."},
            headers=headers_a
        )
        self.assertEqual(r2.status_code, 201)
        self.assertIsNone(r2.json()["image"])
        post2_id = r2.json()["id"]

        # 5. Bob attempts unauthorized update -> 403
        r_unauth = self.client.put(
            f"/posts/{post_id}",
            data={"title": "Hacked Title"},
            headers=headers_b
        )
        self.assertEqual(r_unauth.status_code, 403)

        # 6. Alice updates post with /posts/{id}/update and uploads new image
        new_fake_jpg = io.BytesIO(b"\xff\xd8\xfffake_jpeg_binary_data")
        r_up = self.client.put(
            f"/posts/{post_id}/update",
            data={"title": "FastAPI Masterclass (Updated)", "content": "Updated content with new cover."},
            files={"image": ("new_cover.jpg", new_fake_jpg, "image/jpeg")},
            headers=headers_a
        )
        self.assertEqual(r_up.status_code, 200)
        self.assertEqual(r_up.json()["title"], "FastAPI Masterclass (Updated)")
        self.assertNotEqual(r_up.json()["image"], image_url)

    def test_03_pagination_and_search(self):
        r_a = self.client.post("/auth/login", json={"username": "alice", "password": "password123"})
        headers_a = {"Authorization": f"Bearer {r_a.json()['access_token']}"}

        # Create additional posts for pagination testing
        topics = [
            ("Python Decorators Explained", "How decorators work under the hood in Python."),
            ("SQLAlchemy Relationships", "One-to-many and many-to-many relationship mapping."),
            ("Dockerizing FastAPI", "Containerizing modern Python microservices with Docker."),
            ("Microservices with Python", "Designing distributed architecture in Python."),
            ("FastAPI Authentication Deepdive", "Using OAuth2 and JWT tokens securely.")
        ]
        for title, content in topics:
            self.client.post("/posts", data={"title": title, "content": content}, headers=headers_a)

        # 1. Test pagination: Page 1 with limit 2
        r_p1 = self.client.get("/posts?page=1&limit=2")
        self.assertEqual(r_p1.status_code, 200)
        data_p1 = r_p1.json()
        self.assertEqual(data_p1["page"], 1)
        self.assertEqual(data_p1["limit"], 2)
        self.assertEqual(len(data_p1["items"]), 2)
        self.assertTrue(data_p1["total"] >= 7)
        self.assertTrue(data_p1["total_pages"] >= 4)

        # 2. Test pagination: Page 2 with limit 2
        r_p2 = self.client.get("/posts?page=2&limit=2")
        self.assertEqual(r_p2.status_code, 200)
        data_p2 = r_p2.json()
        self.assertEqual(data_p2["page"], 2)
        self.assertEqual(len(data_p2["items"]), 2)
        # Ensure items on page 1 and page 2 are distinct
        p1_ids = [item["id"] for item in data_p1["items"]]
        p2_ids = [item["id"] for item in data_p2["items"]]
        self.assertEqual(len(set(p1_ids).intersection(set(p2_ids))), 0)

        # 3. Test search query parameter (?search=Docker)
        r_search = self.client.get("/posts?search=Docker")
        self.assertEqual(r_search.status_code, 200)
        data_search = r_search.json()
        self.assertEqual(data_search["total"], 1)
        self.assertEqual(data_search["items"][0]["title"], "Dockerizing FastAPI")

        # 4. Test combined search & pagination (?search=Python&page=1&limit=2)
        r_comb = self.client.get("/posts?search=Python&page=1&limit=2")
        self.assertEqual(r_comb.status_code, 200)
        data_comb = r_comb.json()
        self.assertTrue(data_comb["total"] >= 2)
        self.assertEqual(len(data_comb["items"]), 2)

        # 5. Test search with no matching keyword
        r_empty = self.client.get("/posts?search=NonExistentTermXYZ123")
        self.assertEqual(r_empty.status_code, 200)
        self.assertEqual(r_empty.json()["total"], 0)
        self.assertEqual(len(r_empty.json()["items"]), 0)

        # 6. Test /posts/mine with pagination
        r_mine = self.client.get("/posts/mine?page=1&limit=3", headers=headers_a)
        self.assertEqual(r_mine.status_code, 200)
        self.assertEqual(len(r_mine.json()["items"]), 3)
        self.assertTrue(r_mine.json()["total"] >= 7)

    def test_04_comments_and_likes_flow(self):
        r_a = self.client.post("/auth/login", json={"username": "alice", "password": "password123"})
        headers_a = {"Authorization": f"Bearer {r_a.json()['access_token']}"}

        r_b = self.client.post("/auth/login", json={"username": "bob", "password": "password123"})
        headers_b = {"Authorization": f"Bearer {r_b.json()['access_token']}"}

        # Create post by Alice
        r = self.client.post("/posts", data={"title": "Community Post", "content": "Let's discuss blog features."}, headers=headers_a)
        post_id = r.json()["id"]

        # 1. Bob likes post
        r = self.client.post(f"/posts/{post_id}/like", headers=headers_b)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["liked"])
        self.assertEqual(r.json()["likes_count"], 1)

        # 2. Bob toggles like again (unlikes)
        r = self.client.post(f"/posts/{post_id}/like", headers=headers_b)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["liked"])
        self.assertEqual(r.json()["likes_count"], 0)

        # 3. Bob likes again and uses explicit DELETE /like endpoint
        r = self.client.post(f"/posts/{post_id}/like", headers=headers_b)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["liked"])

        r = self.client.delete(f"/posts/{post_id}/like", headers=headers_b)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["liked"])

        # 4. Bob comments on Alice's post
        r = self.client.post(f"/posts/{post_id}/comments", json={"text": "Super helpful, thanks!"}, headers=headers_b)
        self.assertEqual(r.status_code, 201)
        comment_id = r.json()["id"]

        # 5. Public views comments on post
        r = self.client.get(f"/posts/{post_id}/comments")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 1)

        # 6. Alice deletes comment (Post author is allowed to delete comments on their post)
        r = self.client.delete(f"/posts/{post_id}/comments/{comment_id}", headers=headers_a)
        self.assertEqual(r.status_code, 200)

        # 7. Alice deletes her post
        r = self.client.delete(f"/posts/{post_id}", headers=headers_a)
        self.assertEqual(r.status_code, 200)

        # 8. Post is gone
        r = self.client.get(f"/posts/{post_id}")
        self.assertEqual(r.status_code, 404)

if __name__ == "__main__":
    unittest.main()
