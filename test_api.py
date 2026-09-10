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

    def test_auth_and_crud_flow(self):
        # 1. Register User 1
        r = self.client.post("/auth/register", json={"username": "alice", "email": "alice@mail.com", "password": "pass123"})
        self.assertEqual(r.status_code, 201)
        headers_a = {"Authorization": f"Bearer {r.json()['access_token']}"}

        # 2. Register User 2
        r = self.client.post("/auth/register", json={"username": "bob", "email": "bob@mail.com", "password": "pass123"})
        self.assertEqual(r.status_code, 201)
        headers_b = {"Authorization": f"Bearer {r.json()['access_token']}"}

        # 3. Create Post by Alice
        r = self.client.post("/posts", json={"title": "FastAPI Guide", "content": "Learn FastAPI easily."}, headers=headers_a)
        self.assertEqual(r.status_code, 201)
        post_id = r.json()["id"]

        # 4. Public list posts
        r = self.client.get("/posts")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(len(r.json()) > 0)

        # 5. Bob attempts unauthorized update / delete -> 403
        r = self.client.put(f"/posts/{post_id}", json={"title": "Hacked"}, headers=headers_b)
        self.assertEqual(r.status_code, 403)
        r = self.client.delete(f"/posts/{post_id}", headers=headers_b)
        self.assertEqual(r.status_code, 403)

        # 6. Bob likes Alice's post
        r = self.client.post(f"/posts/{post_id}/like", headers=headers_b)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["liked"])

        # 7. Bob comments on Alice's post
        r = self.client.post(f"/posts/{post_id}/comments", json={"text": "Awesome post!"}, headers=headers_b)
        self.assertEqual(r.status_code, 201)

        # 8. Public view post details
        r = self.client.get(f"/posts/{post_id}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["comments"]), 1)

        # 9. Alice updates her post
        r = self.client.put(f"/posts/{post_id}", json={"title": "FastAPI Guide (Updated)"}, headers=headers_a)
        self.assertEqual(r.status_code, 200)

        # 10. Bob unlikes post
        r = self.client.delete(f"/posts/{post_id}/like", headers=headers_b)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["liked"])

        # 11. Alice deletes her post
        r = self.client.delete(f"/posts/{post_id}", headers=headers_a)
        self.assertEqual(r.status_code, 200)

if __name__ == "__main__":
    unittest.main()
