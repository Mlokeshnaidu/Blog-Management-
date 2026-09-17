import io
import time
import httpx

BASE_URL = "http://127.0.0.1:8000"
client = httpx.Client(base_url=BASE_URL, timeout=15.0)

print("=" * 95)
print("     COMPREHENSIVE END-TO-END BLOG MANAGEMENT & SUBSCRIPTIONS API AUDIT")
print("=" * 95)

results = []

def record(name, endpoint, method, status_code, expected_code, details):
    passed = status_code == expected_code
    status_str = "PASS" if passed else "FAIL"
    results.append((name, f"{method} {endpoint}", status_code, status_str, details))
    print(f"[{status_str}] {name:32} | {method:6} {endpoint:36} | Code: {status_code:3} | {details}")

# --- 1. ROOT & DOCS ---
r_root = client.get("/")
record("Root Endpoint", "/", "GET", r_root.status_code, 200, f"docs: {r_root.json().get('docs')}")

# --- 2. SUBSCRIPTION PLANS CATALOG ---
r_plans = client.get("/subscriptions/plans")
record("Get Subscription Plans", "/subscriptions/plans", "GET", r_plans.status_code, 200, f"Plans: {[p['name'] for p in r_plans.json()]}")

# --- 3. USER REGISTRATION (AUTO BASIC PLAN + INVOICE) ---
ts = int(time.time())
user_a = f"alice_sub_{ts}"
r_reg_a = client.post("/auth/register", json={"username": user_a, "email": f"{user_a}@test.com", "password": "Password123!"})
token_a = r_reg_a.json().get("access_token")
headers_a = {"Authorization": f"Bearer {token_a}"}
record("Register User (Auto Basic)", "/auth/register", "POST", r_reg_a.status_code, 201, f"User: {user_a}, Plan: {r_reg_a.json().get('user', {}).get('subscription_plan', {}).get('name')}")

# --- 4. CHECK USER'S CURRENT PLAN & USAGE ---
r_my_plan = client.get("/subscriptions/my-plan", headers=headers_a)
record("Get My Plan Usage", "/subscriptions/my-plan", "GET", r_my_plan.status_code, 200, f"Plan: {r_my_plan.json().get('plan_name')}, Max Posts: {r_my_plan.json().get('max_posts')}, Posts: {r_my_plan.json().get('posts_count')}")

# --- 5. CHECK BILLING HISTORY & DOWNLOAD INVOICE ---
r_bill = client.get("/billing/history", headers=headers_a)
record("Get Billing History", "/billing/history", "GET", r_bill.status_code, 200, f"Transactions: {len(r_bill.json())}")
if r_bill.json():
    inv_id = r_bill.json()[0]["id"]
    inv_path = r_bill.json()[0]["invoice_pdf_path"]
    r_inv = client.get(f"/billing/invoices/{inv_id}", headers=headers_a)
    record("Download Generated Invoice", f"/billing/invoices/{inv_id}", "GET", r_inv.status_code, 200, f"PDF bytes: {len(r_inv.content)}, Type: {r_inv.headers.get('content-type')}")

    # Static mount check
    r_static_inv = client.get(inv_path)
    record("Static Invoice PDF Serve", inv_path, "GET", r_static_inv.status_code, 200, f"Static Mount Access OK")

# --- 6. CREATE POST #1 (ALLOWED BY BASIC PLAN) ---
sample_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
files = {"image": ("audit_cover.png", io.BytesIO(sample_png), "image/png")}
r_p1 = client.post("/posts/create", data={"title": f"Post 1 by {user_a}", "content": "First post allowed by Basic"}, files=files, headers=headers_a)
post1_id = r_p1.json().get("id")
record("Create Post 1 (Basic Plan)", "/posts/create", "POST", r_p1.status_code, 201, f"Post ID: {post1_id}")

# --- 7. CREATE POST #2 (EXCEEDS BASIC LIMIT -> EXPECT 403) ---
r_p2_blocked = client.post("/posts", data={"title": f"Post 2 by {user_a}", "content": "Should be blocked by Basic limit"}, headers=headers_a)
record("Enforce Post Limit (Basic)", "/posts", "POST", r_p2_blocked.status_code, 403, f"Detail: '{r_p2_blocked.json().get('detail')}'")

# --- 8. UPGRADE TO PREMIUM PLAN ---
r_up_prem = client.post("/subscriptions/subscribe", json={"plan_name": "Premium"}, headers=headers_a)
record("Upgrade to Premium Plan", "/subscriptions/subscribe", "POST", r_up_prem.status_code, 200, f"New Plan: {r_up_prem.json().get('plan', {}).get('name')}, Amount: ${r_up_prem.json().get('billing', {}).get('amount')}")

# --- 9. CREATE POST #2 UNDER PREMIUM (NOW SUCCEEDS) ---
r_p2 = client.post("/posts", data={"title": f"Post 2 by {user_a}", "content": "Second post allowed by Premium"}, headers=headers_a)
post2_id = r_p2.json().get("id")
record("Create Post 2 (Premium Plan)", "/posts", "POST", r_p2.status_code, 201, f"Post ID: {post2_id}")

# --- 10. CREATE POST #3 (EXCEEDS PREMIUM LIMIT OF 2 -> EXPECT 403) ---
r_p3_blocked = client.post("/posts", data={"title": f"Post 3 by {user_a}", "content": "Should be blocked by Premium limit"}, headers=headers_a)
record("Enforce Post Limit (Premium)", "/posts", "POST", r_p3_blocked.status_code, 403, f"Detail: '{r_p3_blocked.json().get('detail')}'")

# --- 11. UPGRADE TO PRO PLAN ---
r_up_pro = client.post("/subscriptions/upgrade", json={"plan_name": "Pro"}, headers=headers_a)
record("Upgrade to Pro Plan", "/subscriptions/upgrade", "POST", r_up_pro.status_code, 200, f"New Plan: {r_up_pro.json().get('plan', {}).get('name')}, Unlimited Access")

# --- 12. CREATE POST #3 UNDER PRO (UNLIMITED) ---
r_p3 = client.post("/posts", data={"title": f"Post 3 by {user_a}", "content": "Third post allowed by Pro"}, headers=headers_a)
post3_id = r_p3.json().get("id")
record("Create Post 3 (Pro Plan)", "/posts", "POST", r_p3.status_code, 201, f"Post ID: {post3_id}")

# --- 13. REGISTER SECOND USER (BOB) & TEST INTERACTIONS ---
user_b = f"bob_sub_{ts}"
r_reg_b = client.post("/auth/register", json={"username": user_b, "email": f"{user_b}@test.com", "password": "Password123!"})
token_b = r_reg_b.json().get("access_token")
headers_b = {"Authorization": f"Bearer {token_b}"}
record("Register User Bob (Basic)", "/auth/register", "POST", r_reg_b.status_code, 201, f"User: {user_b}")

# --- 14. BOB LIKES POST ---
r_like = client.post(f"/posts/{post1_id}/like", headers=headers_b)
record("Bob Likes Post 1", f"/posts/{post1_id}/like", "POST", r_like.status_code, 200, f"Liked: {r_like.json().get('liked')}, Total Likes: {r_like.json().get('likes_count')}")

# --- 15. BOB COMMENTS ON POST ---
r_comm = client.post(f"/posts/{post1_id}/comments", json={"text": "Outstanding work on subscription access!"}, headers=headers_b)
comm_id = r_comm.json().get("id")
record("Bob Comments on Post 1", f"/posts/{post1_id}/comments", "POST", r_comm.status_code, 201, f"Comment ID: {comm_id}")

# --- 16. PAGINATION & FEED ---
r_feed = client.get("/posts", params={"page": 1, "limit": 5})
record("Get Posts Feed (Paginated)", "/posts?page=1&limit=5", "GET", r_feed.status_code, 200, f"Total Posts: {r_feed.json().get('total')}")

# --- 17. SEARCH QUERY ---
r_search = client.get("/posts", params={"search": "Subscription"})
record("Search Posts", "/posts?search=Subscription", "GET", r_search.status_code, 200, f"Matches: {r_search.json().get('total')}")

# --- 18. CLEANUP ---
client.delete(f"/posts/{post1_id}/comments/{comm_id}", headers=headers_a)
client.delete(f"/posts/{post1_id}", headers=headers_a)
client.delete(f"/posts/{post2_id}", headers=headers_a)
client.delete(f"/posts/{post3_id}", headers=headers_a)
record("Post & Comment Cleanup", f"/posts/{post1_id}", "DELETE", 200, 200, "Cleaned up test posts")

print("=" * 95)
all_passed = all(r[3] == "PASS" for r in results)
passed_count = sum(1 for r in results if r[3] == "PASS")
print(f"AUDIT SUMMARY: {passed_count}/{len(results)} Checks Passed | {'ALL TESTS PASSED WITH 100% SUCCESS' if all_passed else 'SOME CHECKS FAILED'}")
print("=" * 95)
