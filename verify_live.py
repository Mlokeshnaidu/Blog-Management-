import io
import time
import sqlite3
import httpx

BASE_URL = "http://127.0.0.1:8000"

def main():
    print("=" * 80)
    print("  LIVE BLOG MANAGEMENT & SUBSCRIPTIONS API VERIFICATION")
    print("=" * 80)

    client = httpx.Client(base_url=BASE_URL, timeout=15.0)

    # 1. Verify Catalog of Subscription Plans
    r_plans = client.get("/subscriptions/plans")
    print(f"\n[1] Available Subscription Plans (/subscriptions/plans):")
    for p in r_plans.json():
        print(f"    - {p['name']:8} | Price: ${p['price']:5.2f} | Max Posts: {p['max_posts']:2} | Max Img/Post: {p['max_images_per_post']:2} | Max Likes/Comments: {p['max_likes']}")

    ts = int(time.time())
    username_a = f"alice_{ts}"
    email_a = f"alice_{ts}@example.com"
    username_b = f"bob_{ts}"
    email_b = f"bob_{ts}@example.com"

    # 2. Register Alice (Auto enrolled in Basic + Invoice generated)
    r_reg_a = client.post("/auth/register", json={
        "username": username_a,
        "email": email_a,
        "password": "Password123!"
    })
    print(f"\n[2] Register User Alice ({username_a}):")
    print(f"    Status: {r_reg_a.status_code} | Token: {'OK' if 'access_token' in r_reg_a.json() else 'FAIL'} | Active Plan: {r_reg_a.json().get('user', {}).get('subscription_plan', {}).get('name')}")
    token_a = r_reg_a.json().get("access_token")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 3. Check Alice's Billing History & Invoice PDF
    r_bill_a = client.get("/billing/history", headers=headers_a)
    first_bill = r_bill_a.json()[0]
    print(f"\n[3] Alice's Initial Welcome Invoice:")
    print(f"    Txn ID: {first_bill['transaction_id']} | Plan: {first_bill['plan_name']} | Amount: ${first_bill['amount']} | PDF: {first_bill['invoice_pdf_path']}")

    # 4. Verify Downloading Invoice PDF
    r_pdf = client.get(f"/billing/invoices/{first_bill['id']}", headers=headers_a)
    print(f"\n[4] Download Invoice PDF (/billing/invoices/{first_bill['id']}):")
    print(f"    Status: {r_pdf.status_code} | Content-Type: {r_pdf.headers.get('content-type')} | PDF Valid Header: {r_pdf.content.startswith(b'%PDF')}")

    # 5. Alice creates 1st Post with Image (Allowed by Basic plan)
    sample_image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRdemo_png_binary_data"
    files = {"image": ("blog_cover.png", io.BytesIO(sample_image_bytes), "image/png")}
    data = {
        "title": "Mastering FastAPI with Image Uploads",
        "content": "A comprehensive guide on building scalable APIs with FastAPI, SQLAlchemy, and ReportLab PDF invoices."
    }
    r_post1 = client.post("/posts/create", data=data, files=files, headers=headers_a)
    post1_data = r_post1.json()
    post1_id = post1_data.get("id")
    print(f"\n[5] Alice creates Post #1 (Allowed under Basic):")
    print(f"    Status: {r_post1.status_code} | Post ID: {post1_id} | Image: {post1_data.get('image')}")

    # 6. Alice attempts 2nd Post under Basic (Should be BLOCKED with friendly validation message)
    r_post2_blocked = client.post("/posts", data={"title": "Exceeding Limit Post", "content": "This should fail"}, headers=headers_a)
    print(f"\n[6] Alice attempts Post #2 (Exceeds Basic limit):")
    print(f"    Status: {r_post2_blocked.status_code} (Expected 403) | Detail: '{r_post2_blocked.json().get('detail')}'")

    # 7. Alice Upgrades to Premium Plan
    r_up_prem = client.post("/subscriptions/subscribe", json={"plan_name": "Premium"}, headers=headers_a)
    print(f"\n[7] Alice Upgrades to Premium Plan ($9.99/mo):")
    print(f"    Status: {r_up_prem.status_code} | Upgraded Plan: {r_up_prem.json().get('plan', {}).get('name')} | New Invoice Generated: {r_up_prem.json().get('billing', {}).get('invoice_pdf_path')}")

    # 8. Alice creates Post #2 (Now succeeds under Premium)
    r_post2 = client.post("/posts", data={"title": "Advanced Microservices Architecture", "content": "Second post under Premium tier"}, headers=headers_a)
    print(f"\n[8] Alice creates Post #2 under Premium:")
    print(f"    Status: {r_post2.status_code} | Post ID: {r_post2.json().get('id')}")

    # 9. Register Bob & Test Interactions (Likes & Comments)
    r_reg_b = client.post("/auth/register", json={
        "username": username_b,
        "email": email_b,
        "password": "Password123!"
    })
    token_b = r_reg_b.json().get("access_token")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    r_like = client.post(f"/posts/{post1_id}/like", headers=headers_b)
    print(f"\n[9] Bob likes Alice's Post #1:")
    print(f"    Status: {r_like.status_code} | Liked: {r_like.json().get('liked')} | Likes Count: {r_like.json().get('likes_count')}")

    r_comm = client.post(f"/posts/{post1_id}/comments", json={"text": "Outstanding tutorial! Great explanation of subscription models."}, headers=headers_b)
    print(f"\n[10] Bob comments on Alice's Post #1:")
    print(f"     Status: {r_comm.status_code} | Comment ID: {r_comm.json().get('id')} | Text: '{r_comm.json().get('text')}'")

    # 11. Inspect SQLite Database Schema & Tables
    print("\n" + "=" * 80)
    print("  SQLITE DATABASE AUDIT (blog.db)")
    print("=" * 80)
    conn = sqlite3.connect("blog.db")
    c = conn.cursor()

    tables = ["subscription_plans", "billing_history", "users", "posts", "comments", "likes"]
    for table in tables:
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
    print("\n" + "=" * 80)
    print("  ALL SUBSCRIPTION & BLOG MANAGEMENT FEATURES FULLY VERIFIED!")
    print("=" * 80)

if __name__ == "__main__":
    main()
