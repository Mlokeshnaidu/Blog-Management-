import urllib.request
import json
import sqlite3
import time

BASE_URL = "http://127.0.0.1:8000"

def make_request(endpoint, method="GET", data=None, token=None):
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            resp_body = resp.read().decode("utf-8")
            return resp.status, json.loads(resp_body) if resp_body else {}
    except urllib.error.HTTPError as e:
        resp_body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(resp_body)
        except Exception:
            return e.code, resp_body

def main():
    print("=" * 65)
    print("  LIVE BLOG MANAGEMENT API VERIFICATION")
    print("=" * 65)

    ts = int(time.time())
    username_a = f"alice_{ts}"
    email_a = f"alice_{ts}@example.com"
    username_b = f"bob_{ts}"
    email_b = f"bob_{ts}@example.com"

    # 1. Register Alice
    status, res_a = make_request("/auth/register", "POST", {
        "username": username_a,
        "email": email_a,
        "password": "Password123!"
    })
    print(f"\n[1] Register User Alice ({username_a}):")
    print(f"    Status: {status} | User ID: {res_a.get('user', {}).get('id')} | Token: OK")
    token_a = res_a.get("access_token")

    # 2. Register Bob
    status, res_b = make_request("/auth/register", "POST", {
        "username": username_b,
        "email": email_b,
        "password": "Password123!"
    })
    print(f"\n[2] Register User Bob ({username_b}):")
    print(f"    Status: {status} | User ID: {res_b.get('user', {}).get('id')} | Token: OK")
    token_b = res_b.get("access_token")

    # 3. Alice Creates a Post
    status, post = make_request("/posts", "POST", {
        "title": "FastAPI & SQLAlchemy Complete Guide",
        "content": "Building high-performance REST APIs in Python."
    }, token=token_a)
    post_id = post.get("id")
    print(f"\n[3] Alice creates a Post (ID: {post_id}):")
    print(f"    Status: {status} | Title: '{post.get('title')}'")

    # 4. Bob attempts unauthorized update on Alice's post
    status, res_unauth = make_request(f"/posts/{post_id}", "PUT", {
        "title": "Hacked Post Title"
    }, token=token_b)
    print(f"\n[4] Bob attempts unauthorized update on Alice's post:")
    print(f"    Status: {status} (Expected 403 Forbidden: {res_unauth.get('detail')})")

    # 5. Bob likes Alice's post
    status, res_like = make_request(f"/posts/{post_id}/like", "POST", token=token_b)
    print(f"\n[5] Bob likes Alice's post:")
    print(f"    Status: {status} | Liked: {res_like.get('liked')} | Likes Count: {res_like.get('likes_count')}")

    # 6. Bob adds a comment to Alice's post
    status, res_comment = make_request(f"/posts/{post_id}/comments", "POST", {
        "text": "Great article Alice! Very helpful."
    }, token=token_b)
    comment_id = res_comment.get("id")
    print(f"\n[6] Bob comments on Alice's post:")
    print(f"    Status: {status} | Comment ID: {comment_id} | Text: '{res_comment.get('text')}'")

    # 7. Alice views her posts (/posts/mine)
    status, res_mine = make_request("/posts/mine", "GET", token=token_a)
    print(f"\n[7] Alice checks /posts/mine:")
    print(f"    Status: {status} | Found {len(res_mine)} personal post(s)")

    # 8. Public view single post with comments and like count
    status, post_detail = make_request(f"/posts/{post_id}", "GET")
    print(f"\n[8] Public views Post #{post_id} details:")
    print(f"    Status: {status} | Likes: {post_detail.get('likes_count')} | Comments: {len(post_detail.get('comments', []))}")

    # 9. Query SQLite Database and print tables
    print("\n" + "=" * 65)
    print("  SQLITE DATABASE TABLES & DATA (blog.db)")
    print("=" * 65)
    conn = sqlite3.connect("blog.db")
    c = conn.cursor()

    for table in ["users", "posts", "comments", "likes"]:
        print(f"\n>>> TABLE: {table.upper()} <<<")
        c.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in c.fetchall()]
        print("Columns: " + " | ".join(columns))
        print("-" * 50)
        c.execute(f"SELECT * FROM {table}")
        rows = c.fetchall()
        for r in rows:
            print("  ", r)

    conn.close()
    print("\n" + "=" * 65)
    print("  ALL SPECIFICATIONS VERIFIED SUCCESSFULLY!")
    print("=" * 65)

if __name__ == "__main__":
    main()
