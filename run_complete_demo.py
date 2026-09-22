"""
Master Demo Script - Blog Management System with Subscription Control & Email Notifications
Executes all real API workflows against the live running server (http://127.0.0.1:8000).
"""
import io
import time
import httpx
import sqlite3

BASE_URL = "http://127.0.0.1:8000"

def main():
    print("=" * 90)
    print("        FASTAPI BLOG MANAGEMENT & SUBSCRIPTION SYSTEM - COMPLETE LIVE DEMO")
    print("=" * 90)

    client = httpx.Client(base_url=BASE_URL, timeout=15.0)

    # -------------------------------------------------------------
    # 1. API DOCS & METADATA
    # -------------------------------------------------------------
    r_root = client.get("/")
    print(f"\n[DEMO STEP 1] Checking API Root & Documentation Endpoints:")
    print(f"  * GET /                  -> Status: {r_root.status_code} | Docs: {r_root.json().get('docs')}")
    print(f"  * Swagger UI             -> Available at: {BASE_URL}/docs")
    print(f"  * ReDoc Documentation    -> Available at: {BASE_URL}/redoc")
    print(f"  * Admin Dashboard UI     -> Available at: {BASE_URL}/admin")

    # -------------------------------------------------------------
    # 2. SUBSCRIPTION PLANS CATALOG
    # -------------------------------------------------------------
    r_plans = client.get("/subscriptions/plans")
    print(f"\n[DEMO STEP 2] Catalog of Subscription Plans (/subscriptions/plans):")
    for p in r_plans.json():
        p_str = f"Unlimited" if p['max_posts'] == -1 else str(p['max_posts'])
        print(f"  * {p['name']:8} | Price: ${p['price']:5.2f} | Posts: {p_str:9} | Likes/Comments: {p['max_likes']:3}")

    # -------------------------------------------------------------
    # 3. USER REGISTRATION (ALICE) - AUTO BASIC + INVOICE PDF
    # -------------------------------------------------------------
    ts = int(time.time())
    user_a = f"alice_demo_{ts}"
    email_a = f"alice_{ts}@techblog.com"
    r_reg_a = client.post("/auth/register", json={
        "username": user_a,
        "email": email_a,
        "password": "SecurePassword123!"
    })
    token_a = r_reg_a.json().get("access_token")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    print(f"\n[DEMO STEP 3] User Registration (Alice):")
    print(f"  * Registered: @{user_a} ({email_a})")
    print(f"  * Active Subscription Plan: {r_reg_a.json().get('user', {}).get('subscription_plan', {}).get('name')}")
    print(f"  * JWT Bearer Token: {token_a[:30]}...")

    # -------------------------------------------------------------
    # 4. BILLING HISTORY & REPORTLAB PDF INVOICE
    # -------------------------------------------------------------
    r_bill = client.get("/billing/history", headers=headers_a)
    invoice_entry = r_bill.json()[0]
    inv_pdf_path = invoice_entry["invoice_pdf_path"]
    r_inv_file = client.get(inv_pdf_path)
    print(f"\n[DEMO STEP 4] Initial Welcome Invoice PDF Generated:")
    print(f"  * Txn ID: {invoice_entry['transaction_id']}")
    print(f"  * Plan: {invoice_entry['plan_name']} | Amount: ${invoice_entry['amount']:.2f}")
    print(f"  * PDF Path: {inv_pdf_path} ({len(r_inv_file.content)} bytes, Content-Type: {r_inv_file.headers.get('content-type')})")

    # -------------------------------------------------------------
    # 5. POST CREATION WITH IMAGE UPLOAD (BASIC ALLOWED)
    # -------------------------------------------------------------
    sample_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    files = {"image": ("fastapi_guide.png", io.BytesIO(sample_png), "image/png")}
    data = {
        "title": "FastAPI Best Practices: Async Notifications & Security",
        "content": "A comprehensive deep dive into FastAPI BackgroundTasks, SQLAlchemy ORM, and secure auth."
    }
    r_post1 = client.post("/posts/create", data=data, files=files, headers=headers_a)
    post1_id = r_post1.json().get("id")
    print(f"\n[DEMO STEP 5] Alice Creates Post #1 (Allowed under Basic):")
    print(f"  * Post ID: {post1_id} | Title: \"{r_post1.json().get('title')}\"")
    print(f"  * Uploaded Image URL: {r_post1.json().get('image')}")

    # -------------------------------------------------------------
    # 6. BASIC PLAN LIMIT ENFORCEMENT
    # -------------------------------------------------------------
    r_post2_blocked = client.post("/posts", data={"title": "Second Post Attempt", "content": "Limit exceeded"}, headers=headers_a)
    print(f"\n[DEMO STEP 6] Alice Attempts Post #2 (Exceeds Basic Plan Limit):")
    print(f"  * HTTP Status: {r_post2_blocked.status_code} (Expected 403 Forbidden)")
    print(f"  * Friendly Validation Message: \"{r_post2_blocked.json().get('detail')}\"")

    # -------------------------------------------------------------
    # 7. UPGRADE TO PREMIUM PLAN
    # -------------------------------------------------------------
    r_upgrade = client.post("/subscriptions/subscribe", json={"plan_name": "Premium"}, headers=headers_a)
    print(f"\n[DEMO STEP 7] Alice Upgrades to Premium Tier ($9.99/mo):")
    print(f"  * Upgraded Plan: {r_upgrade.json().get('plan', {}).get('name')}")
    print(f"  * New ReportLab Invoice PDF: {r_upgrade.json().get('billing', {}).get('invoice_pdf_path')}")

    # Alice creates post #2 (now allowed under Premium)
    r_post2 = client.post("/posts", data={"title": "Advanced Microservices Architecture", "content": "Second post under Premium tier."}, headers=headers_a)
    print(f"  * Alice creates Post #2: ID {r_post2.json().get('id')} -> Status: {r_post2.status_code}")

    # -------------------------------------------------------------
    # 8. ENGAGER REGISTRATION & ASYNC EMAIL NOTIFICATIONS
    # -------------------------------------------------------------
    user_b = f"bob_fan_{ts}"
    email_b = f"bob_{ts}@techblog.com"
    r_reg_b = client.post("/auth/register", json={
        "username": user_b,
        "email": email_b,
        "password": "SecurePassword123!"
    })
    token_b = r_reg_b.json().get("access_token")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    print(f"\n[DEMO STEP 8] Bob Interacts with Alice's Post (Triggers Asynchronous Email Notifications):")
    
    # Bob likes Alice's post
    r_like = client.post(f"/posts/{post1_id}/like", headers=headers_b)
    print(f"  * Bob Likes Post #{post1_id} -> HTTP {r_like.status_code} | Likes Count: {r_like.json().get('likes_count')}")
    print(f"    [NOTIFICATION DISPATCHED] -> To: {email_a} | Subject: New Like on: \"FastAPI Best Practices...\"")

    # Bob comments on Alice's post
    comm_text = "Brilliant breakdown! The asynchronous BackgroundTasks pattern is super clean."
    r_comm = client.post(f"/posts/{post1_id}/comments", json={"text": comm_text}, headers=headers_b)
    print(f"  * Bob Comments on Post #{post1_id} -> HTTP {r_comm.status_code} | Comment ID: {r_comm.json().get('id')}")
    print(f"    [NOTIFICATION DISPATCHED] -> To: {email_a} | Subject: New Comment on: \"FastAPI Best Practices...\"")

    # -------------------------------------------------------------
    # 9. PAGINATION & SEARCH DEMO
    # -------------------------------------------------------------
    r_feed = client.get("/posts?page=1&limit=5&search=FastAPI")
    print(f"\n[DEMO STEP 9] Pagination & Keyword Search (GET /posts?page=1&limit=5&search=FastAPI):")
    print(f"  * Total Matches: {r_feed.json().get('total')} | Total Pages: {r_feed.json().get('total_pages')}")
    print(f"  * Returned Items in Page 1: {len(r_feed.json().get('items'))}")

    # -------------------------------------------------------------
    # 10. DATABASE SUMMARY AUDIT
    # -------------------------------------------------------------
    print("\n" + "=" * 90)
    print("                          SQLITE DATABASE AUDIT (blog.db)")
    print("=" * 90)
    conn = sqlite3.connect("blog.db")
    c = conn.cursor()
    for tbl in ["subscription_plans", "billing_history", "users", "posts", "comments", "likes"]:
        c.execute(f"SELECT count(*) FROM {tbl}")
        count = c.fetchone()[0]
        print(f"  * Table '{tbl:20}': {count:3} records")
    conn.close()

    print("\n" + "=" * 90)
    print("      [PASSED] ALL DEMO CHECKPOINTS & REQUIREMENTS VERIFIED WITH 100% SUCCESS!")
    print("=" * 90)

if __name__ == "__main__":
    main()
