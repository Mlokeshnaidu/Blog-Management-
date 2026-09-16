import io
import time
import httpx

BASE_URL = "http://127.0.0.1:8000"
client = httpx.Client(base_url=BASE_URL, timeout=10.0)

print("=" * 85)
print("             COMPREHENSIVE END-TO-END BLOG MANAGEMENT API AUDIT")
print("=" * 85)

results = []

def record(name, endpoint, method, status_code, expected_code, details):
    passed = status_code == expected_code
    status_str = "PASS" if passed else "FAIL"
    results.append((name, f"{method} {endpoint}", status_code, status_str, details))
    print(f"[{status_str}] {name:30} | {method:6} {endpoint:32} | Code: {status_code} | {details}")

# --- 1. ROOT ---
r_root = client.get("/")
record("Root Endpoint", "/", "GET", r_root.status_code, 200, f"docs: {r_root.json().get('docs')}")

# --- 2. AUTHENTICATION ---
# Login with Lokesh via OAuth2 Form (Swagger UI)
r_login_form = client.post("/auth/login", data={"username": "Lokesh", "password": "Loki@1234"})
token_lokesh = r_login_form.json().get("access_token")
headers_lokesh = {"Authorization": f"Bearer {token_lokesh}"}
record("OAuth2 Form Login (Lokesh)", "/auth/login", "POST", r_login_form.status_code, 200, f"User ID: {r_login_form.json().get('user', {}).get('id')}")

# Login with JSON
r_login_json = client.post("/auth/login", json={"username": "Lokesh", "password": "Loki@1234"})
record("JSON Login (Lokesh)", "/auth/login", "POST", r_login_json.status_code, 200, f"Token received: {bool(r_login_json.json().get('access_token'))}")

# Register new test user
ts = int(time.time())
reg_user = f"auditor_{ts}"
reg_email = f"auditor_{ts}@test.com"
r_reg = client.post("/auth/register", json={"username": reg_user, "email": reg_email, "password": "Password123!"})
token_auditor = r_reg.json().get("access_token")
headers_auditor = {"Authorization": f"Bearer {token_auditor}"}
record("User Registration", "/auth/register", "POST", r_reg.status_code, 201, f"Created: {reg_user}")

# Profile /auth/me
r_me = client.get("/auth/me", headers=headers_lokesh)
record("Get Current User Profile", "/auth/me", "GET", r_me.status_code, 200, f"Username: {r_me.json().get('username')}, Email: {r_me.json().get('email')}")

# --- 3. POST CREATION WITH IMAGE ---
sample_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
files = {"image": ("audit_cover.png", io.BytesIO(sample_png), "image/png")}
post_payload = {
    "title": f"Full Audit Blog Post {ts}",
    "content": "Demonstrating complete end-to-end capabilities with images, comments, and likes."
}
r_create_img = client.post("/posts/create", data=post_payload, files=files, headers=headers_lokesh)
post_id = r_create_img.json().get("id")
image_url = r_create_img.json().get("image")
record("Create Post with Image", "/posts/create", "POST", r_create_img.status_code, 201, f"Post ID: {post_id}, Image: {image_url}")

# --- 4. STATIC FILE SERVING ---
if image_url:
    r_img = client.get(image_url)
    record("Static Image Serving", image_url, "GET", r_img.status_code, 200, f"Size: {len(r_img.content)} bytes, Type: {r_img.headers.get('content-type')}")

# --- 5. CREATE POST WITHOUT IMAGE ---
r_create_noimg = client.post("/posts", data={"title": f"Text Post {ts}", "content": "Text-only article content."}, headers=headers_lokesh)
record("Create Post (Text-Only)", "/posts", "POST", r_create_noimg.status_code, 201, f"Post ID: {r_create_noimg.json().get('id')}")

# --- 6. GET POSTS (FEED) ---
r_feed = client.get("/posts", params={"page": 1, "limit": 5})
record("Get Posts Feed", "/posts?page=1&limit=5", "GET", r_feed.status_code, 200, f"Total: {r_feed.json().get('total')}, Returned: {len(r_feed.json().get('items', []))}")

# --- 7. SEARCH FILTER ---
r_search = client.get("/posts", params={"search": "Audit"})
record("Search Posts", "/posts?search=Audit", "GET", r_search.status_code, 200, f"Matches found: {r_search.json().get('total')}")

# --- 8. GET MY POSTS ---
r_mine = client.get("/posts/mine", headers=headers_lokesh)
record("Get My Posts", "/posts/mine", "GET", r_mine.status_code, 200, f"My posts total: {r_mine.json().get('total')}")

# --- 9. GET SINGLE POST ---
r_single = client.get(f"/posts/{post_id}", headers=headers_lokesh)
record("Get Single Post Detail", f"/posts/{post_id}", "GET", r_single.status_code, 200, f"Title: {r_single.json().get('title')}")

# --- 10. LIKE POST ---
r_like = client.post(f"/posts/{post_id}/like", headers=headers_auditor)
record("Like Post (Auditor User)", f"/posts/{post_id}/like", "POST", r_like.status_code, 200, f"Likes count: {r_like.json().get('likes_count')}")

# --- 11. COMMENT ON POST ---
r_comm = client.post(f"/posts/{post_id}/comments", json={"text": "Excellent article with image demo!"}, headers=headers_auditor)
comment_id = r_comm.json().get("id")
record("Add Comment", f"/posts/{post_id}/comments", "POST", r_comm.status_code, 201, f"Comment ID: {comment_id}, Text: {r_comm.json().get('text')}")

# --- 12. GET COMMENTS ---
r_get_comms = client.get(f"/posts/{post_id}/comments")
record("Get Post Comments", f"/posts/{post_id}/comments", "GET", r_get_comms.status_code, 200, f"Comments count: {len(r_get_comms.json())}")

# --- 13. UPDATE POST ---
r_update = client.put(f"/posts/{post_id}/update", data={"title": f"Full Audit Blog Post (Updated) {ts}"}, headers=headers_lokesh)
record("Update Post Title", f"/posts/{post_id}/update", "PUT", r_update.status_code, 200, f"New Title: {r_update.json().get('title')}")

# --- 14. DELETE COMMENT ---
r_del_comm = client.delete(f"/posts/{post_id}/comments/{comment_id}", headers=headers_auditor)
record("Delete Comment", f"/posts/{post_id}/comments/{comment_id}", "DELETE", r_del_comm.status_code, 200, f"Response: {r_del_comm.json()}")

# --- 15. UNLIKE POST ---
r_unlike = client.delete(f"/posts/{post_id}/like", headers=headers_auditor)
record("Unlike Post", f"/posts/{post_id}/like", "DELETE", r_unlike.status_code, 200, f"Likes count: {r_unlike.json().get('likes_count')}")

# --- 16. DELETE POST ---
r_del_post = client.delete(f"/posts/{post_id}", headers=headers_lokesh)
record("Delete Post & Cleanup", f"/posts/{post_id}", "DELETE", r_del_post.status_code, 200, f"Response: {r_del_post.json()}")

print("=" * 85)
all_passed = all(r[3] == "PASS" for r in results)
passed_count = sum(1 for r in results if r[3] == "PASS")
print(f"AUDIT SUMMARY: {passed_count}/{len(results)} Endpoints Passed | {'ALL TESTS PASSED SUCCESSFULLY' if all_passed else 'SOME TESTS FAILED'}")
print("=" * 85)
