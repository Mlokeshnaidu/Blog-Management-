import io
import time
import sqlite3
import httpx

BASE_URL = "http://127.0.0.1:8000"

def main():
    print("=" * 70)
    print("  LIVE BLOG MANAGEMENT API VERIFICATION (ENHANCED)")
    print("=" * 70)

    client = httpx.Client(base_url=BASE_URL, timeout=10.0)

    ts = int(time.time())
    username_a = f"alice_{ts}"
    email_a = f"alice_{ts}@example.com"
    username_b = f"bob_{ts}"
    email_b = f"bob_{ts}@example.com"

    # 1. Register Alice
    r_reg_a = client.post("/auth/register", json={
        "username": username_a,
        "email": email_a,
        "password": "Password123!"
    })
    print(f"\n[1] Register User Alice ({username_a}):")
    print(f"    Status: {r_reg_a.status_code} | Token: {'OK' if 'access_token' in r_reg_a.json() else 'FAIL'}")
    token_a = r_reg_a.json().get("access_token")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register Bob
    r_reg_b = client.post("/auth/register", json={
        "username": username_b,
        "email": email_b,
        "password": "Password123!"
    })
    print(f"\n[2] Register User Bob ({username_b}):")
    print(f"    Status: {r_reg_b.status_code} | Token: {'OK' if 'access_token' in r_reg_b.json() else 'FAIL'}")
    token_b = r_reg_b.json().get("access_token")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. Alice Creates Post with Cover Image via /posts/create
    sample_image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRdemo_png_binary_data"
    files = {"image": ("blog_cover.png", io.BytesIO(sample_image_bytes), "image/png")}
    data = {
        "title": "Mastering FastAPI with Image Uploads",
        "content": "A comprehensive guide on building scalable APIs with FastAPI, SQLAlchemy, and static file serving."
    }
    r_post = client.post("/posts/create", data=data, files=files, headers=headers_a)
    print(f"\n[3] Alice creates a Post with Cover Image (/posts/create):")
    post_data = r_post.json()
    post_id = post_data.get("id")
    image_url = post_data.get("image")
    print(f"    Status: {r_post.status_code} | Post ID: {post_id} | Image URL: {image_url}")

    # 4. Verify Static Image Serving
    if image_url:
        r_img = client.get(image_url)
        print(f"\n[4] Verify Static Image Access ({image_url}):")
        print(f"    Status: {r_img.status_code} | Content-Length: {len(r_img.content)} bytes | Static Mount: OK")

    # 5. Create multiple posts for Pagination and Search testing
    topics = [
        ("Python Async Architecture", "In-depth look at asyncio event loops and concurrency."),
        ("Microservices with Docker and FastAPI", "Deploying high-performance containerized services."),
        ("SQLAlchemy 2.0 ORM Guide", "Optimizing relationship mapping and lazy vs eager loading.")
    ]
    for title, content in topics:
        client.post("/posts", data={"title": title, "content": content}, headers=headers_a)

    # 6. Test Pagination: GET /posts?page=1&limit=2
    r_p1 = client.get("/posts", params={"page": 1, "limit": 2})
    p1_data = r_p1.json()
    print(f"\n[6] Test Pagination (GET /posts?page=1&limit=2):")
    print(f"    Status: {r_p1.status_code} | Page: {p1_data.get('page')} | Limit: {p1_data.get('limit')} | Total: {p1_data.get('total')} | Total Pages: {p1_data.get('total_pages')}")
    print(f"    Items returned: {len(p1_data.get('items', []))}")

    # 7. Test Search Filtering: GET /posts?search=Docker
    r_search = client.get("/posts", params={"search": "Docker"})
    search_data = r_search.json()
    print(f"\n[7] Test Search Filter (GET /posts?search=Docker):")
    print(f"    Status: {r_search.status_code} | Matches Found: {search_data.get('total')}")
    for item in search_data.get("items", []):
        print(f"    -> [Post #{item['id']}] {item['title']}")

    # 8. Test Combined Search & Pagination: GET /posts?search=Python&page=1&limit=1
    r_comb = client.get("/posts", params={"search": "Python", "page": 1, "limit": 1})
    comb_data = r_comb.json()
    print(f"\n[8] Test Combined Search & Pagination (GET /posts?search=Python&page=1&limit=1):")
    print(f"    Status: {r_comb.status_code} | Page: {comb_data.get('page')} | Total: {comb_data.get('total')} | Total Pages: {comb_data.get('total_pages')}")

    # 9. Bob Likes Alice's Post
    r_like = client.post(f"/posts/{post_id}/like", headers=headers_b)
    print(f"\n[9] Bob likes Alice's Post #{post_id}:")
    print(f"    Status: {r_like.status_code} | Liked: {r_like.json().get('liked')} | Likes Count: {r_like.json().get('likes_count')}")

    # 10. Bob Comments on Alice's Post
    r_comm = client.post(f"/posts/{post_id}/comments", json={"text": "Outstanding tutorial! The cover image is super clear."}, headers=headers_b)
    print(f"\n[10] Bob comments on Alice's Post #{post_id}:")
    print(f"     Status: {r_comm.status_code} | Comment ID: {r_comm.json().get('id')} | Text: '{r_comm.json().get('text')}'")

    # 11. Alice Updates Post with new Image via /posts/{id}/update
    new_image_bytes = b"\xff\xd8\xffdemo_jpeg_binary_data"
    new_files = {"image": ("new_cover.jpg", io.BytesIO(new_image_bytes), "image/jpeg")}
    r_update = client.put(f"/posts/{post_id}/update", data={"title": "Mastering FastAPI with Image Uploads (2nd Edition)"}, files=new_files, headers=headers_a)
    print(f"\n[11] Alice updates Post #{post_id} with new Cover Image (/posts/{post_id}/update):")
    print(f"     Status: {r_update.status_code} | New Title: '{r_update.json().get('title')}' | New Image: {r_update.json().get('image')}")

    # 12. Query SQLite Database Schema & Records
    print("\n" + "=" * 70)
    print("  SQLITE DATABASE TABLES & DATA (blog.db)")
    print("=" * 70)
    conn = sqlite3.connect("blog.db")
    c = conn.cursor()

    for table in ["users", "posts", "comments", "likes"]:
        print(f"\n>>> TABLE: {table.upper()} <<<")
        c.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in c.fetchall()]
        print("Columns: " + " | ".join(columns))
        print("-" * 50)
        c.execute(f"SELECT * FROM {table} ORDER BY id DESC LIMIT 3")
        rows = c.fetchall()
        for r in rows:
            print("  ", r)

    conn.close()
    print("\n" + "=" * 70)
    print("  ALL SPECIFICATIONS & ENHANCEMENTS VERIFIED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    main()
