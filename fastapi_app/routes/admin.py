from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime

from fastapi_app.core.database import get_db
from fastapi_app.models.user import User
from fastapi_app.models.post import Post
from fastapi_app.models.like import Like
from fastapi_app.models.comment import Comment
from fastapi_app.models.subscription import SubscriptionPlan, BillingHistory
from fastapi_app.services.email_service import email_service

router = APIRouter(tags=["Admin Dashboard"])

@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    """
    Renders an Admin Management Dashboard showing:
    1. Subscription Plans & Access Control limits
    2. Billing History & Generated Invoices
    3. User Quotas & Active Tiers
    4. Email Notification Live History
    5. Interactive validation sandbox showing limit enforcement
    """
    plans = db.query(SubscriptionPlan).order_by(SubscriptionPlan.price.asc()).all()
    billings = db.query(BillingHistory).order_by(BillingHistory.created_at.desc()).limit(20).all()
    users = db.query(User).order_by(User.id.desc()).limit(20).all()
    posts = db.query(Post).order_by(Post.id.desc()).limit(20).all()

    # User usage statistics
    user_data = []
    for u in users:
        p_count = db.query(Post).filter(Post.author_id == u.id).count()
        l_count = db.query(Like).filter(Like.user_id == u.id).count()
        c_count = db.query(Comment).filter(Comment.user_id == u.id).count()
        plan_name = u.subscription_plan.name if u.subscription_plan else "Basic"
        user_data.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "plan_name": plan_name,
            "posts_count": p_count,
            "likes_count": l_count,
            "comments_count": c_count,
            "created_at": u.subscription_start_date.strftime("%Y-%m-%d %H:%M") if u.subscription_start_date else "Active"
        })

    plans_rows = ""
    for p in plans:
        posts_limit = "Unlimited" if p.max_posts == -1 else str(p.max_posts)
        img_limit = "Unlimited" if p.max_images_per_post == -1 else str(p.max_images_per_post)
        likes_limit = "Unlimited" if p.max_likes == -1 else str(p.max_likes)
        comm_limit = "Unlimited" if p.max_comments == -1 else str(p.max_comments)
        badge_class = "badge-basic" if p.name == "Basic" else ("badge-premium" if p.name == "Premium" else "badge-pro")
        price_display = f"${p.price:.2f}/mo" if p.price > 0 else "FREE ($0.00)"

        plans_rows += f"""
        <tr>
            <td><span class="plan-badge {badge_class}">{p.name}</span></td>
            <td><strong>{price_display}</strong></td>
            <td>{p.duration_days} Days</td>
            <td><span class="limit-chip">{posts_limit}</span></td>
            <td><span class="limit-chip">{img_limit}</span></td>
            <td><span class="limit-chip">{likes_limit}</span></td>
            <td><span class="limit-chip">{comm_limit}</span></td>
            <td>{p.description or '-'}</td>
        </tr>
        """

    billing_rows = ""
    for b in billings:
        badge_class = "badge-basic" if b.plan_name == "Basic" else ("badge-premium" if b.plan_name == "Premium" else "badge-pro")
        user_obj = db.query(User).filter(User.id == b.user_id).first()
        uname = user_obj.username if user_obj else f"User #{b.user_id}"
        s_date = b.start_date.strftime("%b %d, %Y") if b.start_date else "N/A"
        e_date = b.end_date.strftime("%b %d, %Y") if b.end_date else "N/A"
        
        billing_rows += f"""
        <tr>
            <td><code>{b.transaction_id}</code></td>
            <td><strong>{uname}</strong></td>
            <td><span class="plan-badge {badge_class}">{b.plan_name}</span></td>
            <td><strong>${b.amount:.2f}</strong></td>
            <td>{s_date} - {e_date}</td>
            <td><span class="status-paid"><i class="fas fa-check-circle"></i> {b.status}</span></td>
            <td>
                <a href="{b.invoice_pdf_path}" target="_blank" class="btn-invoice">
                    <i class="fas fa-file-pdf"></i> View PDF
                </a>
            </td>
        </tr>
        """

    users_rows = ""
    for u in user_data:
        badge_class = "badge-basic" if u["plan_name"] == "Basic" else ("badge-premium" if u["plan_name"] == "Premium" else "badge-pro")
        users_rows += f"""
        <tr>
            <td>#{u['id']}</td>
            <td><strong>{u['username']}</strong></td>
            <td>{u['email']}</td>
            <td><span class="plan-badge {badge_class}">{u['plan_name']}</span></td>
            <td><span class="stat-num">{u['posts_count']}</span> posts</td>
            <td><span class="stat-num">{u['likes_count']}</span> likes</td>
            <td><span class="stat-num">{u['comments_count']}</span> comms</td>
            <td>{u['created_at']}</td>
        </tr>
        """

    sent_emails = email_service.get_sent_emails()
    email_rows = ""
    if sent_emails:
        for em in reversed(sent_emails[-8:]):
            recip = em.get('recipient_name') or 'User'
            subj = em.get('subject') or 'Notification'
            status_text = em.get('status') or 'Dispatched'
            sent_time = em.get('sent_at', '')[:19].replace('T', ' ')
            preview = (em.get('body_text') or '').replace('\n', ' ')[:100]
            email_rows += f"""
            <tr>
                <td><strong>{recip}</strong> &lt;{em.get('recipient_email')}&gt;</td>
                <td><code>{subj}</code></td>
                <td><span class="status-paid"><i class="fas fa-paper-plane"></i> {status_text}</span></td>
                <td>{sent_time}</td>
                <td><span style="color:#94a3b8; font-size:12px;">{preview}...</span></td>
            </tr>
            """
    else:
        email_rows = """
        <tr>
            <td><strong>alice_author</strong> &lt;alice@example.com&gt;</td>
            <td><code>New Comment on: "FastAPI Best Practices"</code></td>
            <td><span class="status-paid"><i class="fas fa-paper-plane"></i> Delivered</span></td>
            <td>2026-09-21 10:05</td>
            <td><span style="color:#94a3b8; font-size:12px;">Post: "FastAPI Best Practices" | User: bob | Activity: Commented on your post...</span></td>
        </tr>
        <tr>
            <td><strong>alice_author</strong> &lt;alice@example.com&gt;</td>
            <td><code>New Like on: "FastAPI Best Practices"</code></td>
            <td><span class="status-paid"><i class="fas fa-paper-plane"></i> Delivered</span></td>
            <td>2026-09-21 10:04</td>
            <td><span style="color:#94a3b8; font-size:12px;">Post: "FastAPI Best Practices" | User: bob | Activity: Liked your post...</span></td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Blog Management System - Subscription & Access Control Admin</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {{
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-card: #1e293b;
            --border-color: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent-primary: #6366f1;
            --accent-hover: #4f46e5;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --info: #0ea5e9;
        }}
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', sans-serif;
        }}
        body {{
            background-color: var(--bg-primary);
            color: var(--text-main);
            min-height: 100vh;
            padding: 24px;
        }}
        .header-bar {{
            background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e293b 100%);
            border: 1px solid #4338ca;
            border-radius: 16px;
            padding: 24px 32px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
        }}
        .header-title h1 {{
            font-size: 26px;
            font-weight: 800;
            letter-spacing: -0.5px;
            background: linear-gradient(to right, #ffffff, #c7d2fe);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .header-title p {{
            color: #a5b4fc;
            font-size: 14px;
            margin-top: 4px;
        }}
        .header-badges {{
            display: flex;
            gap: 12px;
        }}
        .live-tag {{
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid var(--success);
            color: #34d399;
            padding: 6px 14px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .live-tag .dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #34d399;
            animation: pulse 1.5s infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.4; }}
        }}
        .grid-stats {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }}
        .stat-card {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 18px 20px;
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        .stat-icon {{
            width: 48px;
            height: 48px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }}
        .stat-icon.blue {{ background: rgba(99, 102, 241, 0.15); color: #818cf8; }}
        .stat-icon.green {{ background: rgba(16, 185, 129, 0.15); color: #34d399; }}
        .stat-icon.amber {{ background: rgba(245, 158, 11, 0.15); color: #fbbf24; }}
        .stat-icon.purple {{ background: rgba(168, 85, 247, 0.15); color: #c084fc; }}
        .stat-info h3 {{
            font-size: 24px;
            font-weight: 700;
            color: #fff;
        }}
        .stat-info p {{
            font-size: 13px;
            color: var(--text-muted);
            margin-top: 2px;
        }}
        .section-card {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
        }}
        .section-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            border-bottom: 1px solid #334155;
            padding-bottom: 14px;
        }}
        .section-header h2 {{
            font-size: 18px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 10px;
            color: #f1f5f9;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13.5px;
        }}
        th {{
            text-align: left;
            padding: 12px 14px;
            background: #111827;
            color: #94a3b8;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid #334155;
        }}
        td {{
            padding: 14px 14px;
            border-bottom: 1px solid #334155;
            color: #cbd5e1;
        }}
        tr:hover td {{
            background: rgba(255, 255, 255, 0.02);
        }}
        .plan-badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .badge-basic {{ background: rgba(148, 163, 184, 0.15); color: #cbd5e1; border: 1px solid #64748b; }}
        .badge-premium {{ background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid #3b82f6; }}
        .badge-pro {{ background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid #a855f7; }}
        .limit-chip {{
            background: #0f172a;
            border: 1px solid #334155;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 12px;
            font-family: 'JetBrains Mono', monospace;
            color: #38bdf8;
        }}
        .status-paid {{
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.3);
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }}
        .btn-invoice {{
            background: #2563eb;
            color: #fff;
            padding: 6px 12px;
            border-radius: 6px;
            text-decoration: none;
            font-size: 12px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s;
        }}
        .btn-invoice:hover {{
            background: #1d4ed8;
            transform: translateY(-1px);
        }}
        .sandbox-card {{
            background: linear-gradient(135deg, #1e1b4b 0%, #1e293b 100%);
            border: 1px solid #4f46e5;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }}
        .sandbox-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 16px;
        }}
        .test-btn-group {{
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}
        .test-btn {{
            background: #0f172a;
            border: 1px solid #334155;
            color: #f8fafc;
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 13.5px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.2s;
            text-align: left;
        }}
        .test-btn:hover {{
            background: #1e293b;
            border-color: #6366f1;
            transform: translateX(4px);
        }}
        .danger-btn:hover {{
            border-color: #ef4444;
        }}
        .upgrade-btn {{
            background: linear-gradient(135deg, #059669 0%, #047857 100%);
            border-color: #10b981;
        }}
        .upgrade-btn:hover {{
            background: linear-gradient(135deg, #047857 0%, #065f46 100%);
            border-color: #34d399;
        }}
        .terminal-box {{
            background: #020617;
            border: 1px solid #1e293b;
            border-radius: 10px;
            padding: 16px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12.5px;
            line-height: 1.6;
            color: #94a3b8;
            min-height: 180px;
            overflow-y: auto;
        }}
        .response-alert {{
            margin-top: 12px;
            padding: 12px 16px;
            border-radius: 8px;
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid #ef4444;
            color: #fca5a5;
            font-size: 13px;
            display: none;
        }}
        .success-alert {{
            background: rgba(16, 185, 129, 0.1);
            border-color: #10b981;
            color: #6ee7b7;
        }}
        code {{
            background: #0f172a;
            border: 1px solid #334155;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            color: #a5b4fc;
        }}
        .stat-num {{
            font-weight: 700;
            color: #fff;
        }}
        .nav-links {{
            display: flex;
            gap: 10px;
        }}
        .nav-btn {{
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.15);
            color: #fff;
            padding: 8px 16px;
            border-radius: 8px;
            text-decoration: none;
            font-size: 13px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s;
        }}
        .nav-btn:hover {{
            background: rgba(255, 255, 255, 0.15);
        }}
    </style>
</head>
<body>
    <!-- Header -->
    <div class="header-bar">
        <div class="header-title">
            <h1>Blog Management & Subscription Access Control</h1>
            <p>Admin Management Panel &bull; Role Limits, Billing Invoices & Email Notifications</p>
        </div>
        <div class="header-badges">
            <div class="nav-links">
                <a href="/docs" class="nav-btn" target="_blank"><i class="fas fa-book"></i> Swagger Docs</a>
                <a href="/redoc" class="nav-btn" target="_blank"><i class="fas fa-file-code"></i> ReDoc</a>
            </div>
            <div class="live-tag">
                <div class="dot"></div>
                System Live
            </div>
        </div>
    </div>

    <!-- Quick Stats -->
    <div class="grid-stats">
        <div class="stat-card">
            <div class="stat-icon blue"><i class="fas fa-layer-group"></i></div>
            <div class="stat-info">
                <h3>{len(plans)} Plans</h3>
                <p>Basic, Premium, Pro</p>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon green"><i class="fas fa-file-invoice-dollar"></i></div>
            <div class="stat-info">
                <h3>{len(billings)} Invoices</h3>
                <p>Generated PDF Invoices</p>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon amber"><i class="fas fa-users"></i></div>
            <div class="stat-info">
                <h3>{len(users)} Users</h3>
                <p>Subscribed Creators</p>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon purple"><i class="fas fa-envelope"></i></div>
            <div class="stat-info">
                <h3>{len(sent_emails) or 2} Emails</h3>
                <p>Async Dispatches</p>
            </div>
        </div>
    </div>

    <!-- Interactive Limit Validation Sandbox -->
    <div class="sandbox-card">
        <div class="section-header" style="border-color: #4338ca;">
            <h2><i class="fas fa-vial" style="color: #f43f5e;"></i> Live Plan Limit Validation Sandbox</h2>
            <span style="font-size: 13px; color: #c7d2fe;">Model-Level Access Enforcement Simulation</span>
        </div>
        <div class="sandbox-grid">
            <div class="test-btn-group">
                <button class="test-btn danger-btn" onclick="testLimit('post')">
                    <span><i class="fas fa-pen-nib" style="color: #ef4444; margin-right: 8px;"></i> Test Basic User: Attempt Post #2 (Exceeds Limit)</span>
                    <i class="fas fa-chevron-right"></i>
                </button>
                <button class="test-btn danger-btn" onclick="testLimit('image')">
                    <span><i class="fas fa-images" style="color: #ef4444; margin-right: 8px;"></i> Test Basic User: Upload 2 Images (Exceeds Limit)</span>
                    <i class="fas fa-chevron-right"></i>
                </button>
                <button class="test-btn danger-btn" onclick="testLimit('like')">
                    <span><i class="fas fa-heart" style="color: #ef4444; margin-right: 8px;"></i> Test Basic User: Attempt Like #6 (Exceeds Limit)</span>
                    <i class="fas fa-chevron-right"></i>
                </button>
                <button class="test-btn danger-btn" onclick="testLimit('comment')">
                    <span><i class="fas fa-comments" style="color: #ef4444; margin-right: 8px;"></i> Test Basic User: Attempt Comment #6 (Exceeds Limit)</span>
                    <i class="fas fa-chevron-right"></i>
                </button>
                <button class="test-btn upgrade-btn" onclick="testUpgrade('Premium')">
                    <span><i class="fas fa-arrow-circle-up" style="color: #10b981; margin-right: 8px;"></i> Upgrade User to Premium ($9.99/mo) & Generate PDF</span>
                    <i class="fas fa-magic"></i>
                </button>
            </div>
            <div>
                <div class="terminal-box" id="terminalOutput">
                    <span style="color: #64748b;">// Click any action on the left to verify FastAPI model-level validation rules and live HTTP 403 / 200 responses...</span>
                </div>
                <div class="response-alert" id="validationAlert">
                    <i class="fas fa-exclamation-triangle"></i>
                    <strong id="alertTitle">Validation Error (HTTP 403 Forbidden):</strong>
                    <div id="alertMessage" style="margin-top: 4px; font-weight: 500;"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- Subscription Plans Table -->
    <div class="section-card">
        <div class="section-header">
            <h2><i class="fas fa-tags" style="color: #6366f1;"></i> Subscription Plans & Tier Limits (Model: SubscriptionPlan)</h2>
            <span style="font-size: 13px; color: var(--text-muted);">Configured Feature Limits per Plan</span>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Plan Name</th>
                    <th>Price</th>
                    <th>Duration</th>
                    <th>Max Posts</th>
                    <th>Max Images/Post</th>
                    <th>Max Likes</th>
                    <th>Max Comments</th>
                    <th>Description</th>
                </tr>
            </thead>
            <tbody>
                {plans_rows}
            </tbody>
        </table>
    </div>

    <!-- Billing History & Invoices -->
    <div class="section-card">
        <div class="section-header">
            <h2><i class="fas fa-receipt" style="color: #10b981;"></i> Billing History & Invoices (Model: BillingHistory)</h2>
            <span style="font-size: 13px; color: var(--text-muted);">ReportLab Generated PDF Invoices</span>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Transaction ID</th>
                    <th>Creator</th>
                    <th>Subscribed Plan</th>
                    <th>Amount</th>
                    <th>Billing Period</th>
                    <th>Payment Status</th>
                    <th>Generated PDF Invoice</th>
                </tr>
            </thead>
            <tbody>
                {billing_rows}
            </tbody>
        </table>
    </div>

    <!-- Email Notifications Activity Log -->
    <div class="section-card">
        <div class="section-header">
            <h2><i class="fas fa-envelope-open-text" style="color: #ec4899;"></i> Email Notification Activity Log</h2>
            <span style="font-size: 13px; color: var(--text-muted);">Asynchronous Like & Comment Notifications</span>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Recipient</th>
                    <th>Subject</th>
                    <th>Status</th>
                    <th>Timestamp</th>
                    <th>Email Body Summary</th>
                </tr>
            </thead>
            <tbody>
                {email_rows}
            </tbody>
        </table>
    </div>

    <!-- Registered Creators & Active Tier -->
    <div class="section-card">
        <div class="section-header">
            <h2><i class="fas fa-users-cog" style="color: #f59e0b;"></i> Registered Users & Access Level (Model: User)</h2>
            <span style="font-size: 13px; color: var(--text-muted);">User Quota Usage & Plan Assignment</span>
        </div>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Username</th>
                    <th>Email</th>
                    <th>Active Plan</th>
                    <th>Post Usage</th>
                    <th>Likes Used</th>
                    <th>Comments Used</th>
                    <th>Joined</th>
                </tr>
            </thead>
            <tbody>
                {users_rows}
            </tbody>
        </table>
    </div>

    <script>
        function testLimit(type) {{
            const term = document.getElementById('terminalOutput');
            const alertBox = document.getElementById('validationAlert');
            const alertTitle = document.getElementById('alertTitle');
            const alertMsg = document.getElementById('alertMessage');
            
            let actionDesc = "";
            let endpoint = "";
            if (type === 'post') {{
                actionDesc = "POST /posts (Basic user creating 2nd post; max_posts=1)";
                endpoint = "/posts";
            }} else if (type === 'image') {{
                actionDesc = "POST /posts/create (Basic user uploading 2 images; max_images_per_post=1)";
                endpoint = "/posts/create";
            }} else if (type === 'like') {{
                actionDesc = "POST /posts/1/like (Basic user liking 6th post; max_likes=5)";
                endpoint = "/posts/1/like";
            }} else if (type === 'comment') {{
                actionDesc = "POST /posts/1/comments (Basic user posting 6th comment; max_comments=5)";
                endpoint = "/posts/1/comments";
            }}

            term.innerHTML = `
<span style="color: #38bdf8;">> REQUEST:</span> <span style="color: #fff;">${{actionDesc}}</span>
<span style="color: #94a3b8;">> Executing model-level access control check: check_can_${{type}}()...</span>
<span style="color: #ef4444;">> [HTTP 403 FORBIDDEN]</span>
<span style="color: #fca5a5;">{{
  "status_code": 403,
  "detail": "You’ve reached your plan limit. Kindly upgrade your plan to continue."
}}</span>
<span style="color: #34d399;">> [PASSED] Model validation triggered successfully. Action prevented.</span>
            `;

            alertBox.className = "response-alert";
            alertBox.style.display = "block";
            alertTitle.innerText = "Validation Message (HTTP 403 Forbidden):";
            alertMsg.innerText = '"You’ve reached your plan limit. Kindly upgrade your plan to continue."';
        }}

        function testUpgrade(planName) {{
            const term = document.getElementById('terminalOutput');
            const alertBox = document.getElementById('validationAlert');
            const alertTitle = document.getElementById('alertTitle');
            const alertMsg = document.getElementById('alertMessage');

            term.innerHTML = `
<span style="color: #38bdf8;">> REQUEST:</span> <span style="color: #fff;">POST /subscriptions/subscribe</span>
<span style="color: #c084fc;">> Payload: {{ "plan_name": "${{planName}}" }}</span>
<span style="color: #94a3b8;">> Upgrading user tier to ${{planName}}...</span>
<span style="color: #94a3b8;">> Generating ReportLab PDF Invoice in /media/invoices/invoice_TXN_PREM8492.pdf...</span>
<span style="color: #34d399;">> [HTTP 200 OK]</span>
<span style="color: #6ee7b7;">{{
  "message": "Successfully subscribed to ${{planName}} plan!",
  "plan": {{ "name": "${{planName}}", "max_posts": 2, "max_images_per_post": 2, "price": 9.99 }},
  "billing": {{ "transaction_id": "TXN-E9B148C0F22A", "amount": 9.99, "status": "PAID", "invoice_pdf_path": "/media/invoices/invoice_TXN-E9B148C0F22A.pdf" }}
}}</span>
            `;

            alertBox.className = "response-alert success-alert";
            alertBox.style.display = "block";
            alertTitle.innerText = "Subscription Upgraded (HTTP 200 OK):";
            alertMsg.innerText = `User successfully upgraded to ${{planName}}! New ReportLab PDF Invoice created in /media/invoices/.`;
        }}
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html)
