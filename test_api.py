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

app.dependency_overrides[get_db] = override_db

class TestBlogAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=engine)

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

    def test_02_posts_crud_and_ownership(self):
        # Login tokens
        r_a = self.client.post("/auth/login", json={"username": "alice", "password": "password123"})
        headers_a = {"Authorization": f"Bearer {r_a.json()['access_token']}"}

        r_b = self.client.post("/auth/login", json={"username": "bob", "password": "password123"})
        headers_b = {"Authorization": f"Bearer {r_b.json()['access_token']}"}

        # 1. Create Post by Alice
        r = self.client.post("/posts", json={"title": "FastAPI Guide", "content": "Learn FastAPI easily."}, headers=headers_a)
        self.assertEqual(r.status_code, 201)
        post_id = r.json()["id"]

        # 2. Public view posts
        r = self.client.get("/posts")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(len(r.json()) >= 1)

        # 3. Filter posts with query search
        r = self.client.get("/posts?q=FastAPI")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(len(r.json()) >= 1)

        # 4. View single post
        r = self.client.get(f"/posts/{post_id}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["title"], "FastAPI Guide")

        # 5. /posts/mine endpoint for Alice
        r = self.client.get("/posts/mine", headers=headers_a)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 1)

        # 6. /posts/mine endpoint for Bob (empty)
        r = self.client.get("/posts/mine", headers=headers_b)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 0)

        # 7. Bob attempts unauthorized update -> 403
        r = self.client.put(f"/posts/{post_id}", json={"title": "Hacked Title"}, headers=headers_b)
        self.assertEqual(r.status_code, 403)

        # 8. Bob attempts unauthorized delete -> 403
        r = self.client.delete(f"/posts/{post_id}", headers=headers_b)
        self.assertEqual(r.status_code, 403)

        # 9. Alice updates post
        r = self.client.put(f"/posts/{post_id}", json={"title": "FastAPI Masterclass", "content": "Updated content."}, headers=headers_a)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["title"], "FastAPI Masterclass")

    def test_03_comments_and_likes_flow(self):
        r_a = self.client.post("/auth/login", json={"username": "alice", "password": "password123"})
        headers_a = {"Authorization": f"Bearer {r_a.json()['access_token']}"}

        r_b = self.client.post("/auth/login", json={"username": "bob", "password": "password123"})
        headers_b = {"Authorization": f"Bearer {r_b.json()['access_token']}"}

        # Create post by Alice
        r = self.client.post("/posts", json={"title": "SQLAlchemy ORM", "content": "Deep dive into models."}, headers=headers_a)
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
