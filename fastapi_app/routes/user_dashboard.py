from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from fastapi_app.core.database import get_db
from fastapi_app.core.security import get_current_user, get_optional_current_user, create_access_token
from fastapi_app.models.user import User
from fastapi_app.models.post import Post
from fastapi_app.models.like import Like
from fastapi_app.models.comment import Comment
from fastapi_app.schemas.dashboard import (
    UserDashboardResponse,
    UserStatsOverview,
    PostAnalyticsItem,
    TimeActivityPoint,
    QuotaUsage,
    EngagementDistribution
)

router = APIRouter(tags=["User Dashboard & Analytics"])


def calculate_user_dashboard_data(user: User, db: Session, days_filter: Optional[int] = None) -> dict:
    """
    Computes all analytics and activity metrics strictly isolated for the given user.
    """
    # 1. Base user posts query
    posts_query = db.query(Post).filter(Post.author_id == user.id)
    now = datetime.now(timezone.utc)
    cutoff_date = None
    if days_filter and days_filter > 0:
        cutoff_date = now - timedelta(days=days_filter)
        posts_query = posts_query.filter(Post.created_at >= cutoff_date)

    user_posts = posts_query.order_by(Post.created_at.desc()).all()
    user_post_ids = [p.id for p in user_posts]

    # 2. Activity metrics
    total_posts = len(user_posts)
    total_views = sum((p.views or 0) for p in user_posts)

    # Comments made by this user
    comments_made_q = db.query(Comment).filter(Comment.user_id == user.id)
    if cutoff_date:
        comments_made_q = comments_made_q.filter(Comment.created_at >= cutoff_date)
    total_comments_made = comments_made_q.count()

    # Likes given by this user
    likes_given_q = db.query(Like).filter(Like.user_id == user.id)
    total_likes_given = likes_given_q.count()

    # Comments & Likes received on user's posts
    if user_post_ids:
        likes_recv_q = db.query(Like).filter(Like.post_id.in_(user_post_ids))
        total_likes_received = likes_recv_q.count()

        comm_recv_q = db.query(Comment).filter(Comment.post_id.in_(user_post_ids))
        if cutoff_date:
            comm_recv_q = comm_recv_q.filter(Comment.created_at >= cutoff_date)
        total_comments_received = comm_recv_q.count()
    else:
        total_likes_received = 0
        total_comments_received = 0

    # Averages & rates
    avg_likes = round(total_likes_received / total_posts, 2) if total_posts > 0 else 0.0
    avg_comments = round(total_comments_received / total_posts, 2) if total_posts > 0 else 0.0
    engagement_rate = round(((total_likes_received + total_comments_received) / max(total_views, 1)) * 100, 2)

    overview = {
        "total_posts": total_posts,
        "total_comments_made": total_comments_made,
        "total_comments_received": total_comments_received,
        "total_likes_received": total_likes_received,
        "total_likes_given": total_likes_given,
        "total_post_views": total_views,
        "avg_likes_per_post": avg_likes,
        "avg_comments_per_post": avg_comments,
        "engagement_rate": engagement_rate
    }

    # 3. Post analytics items
    post_analytics_list = []
    for p in user_posts:
        l_cnt = len(p.likes) if p.likes else 0
        c_cnt = len(p.comments) if p.comments else 0
        p_views = p.views or 0
        post_analytics_list.append({
            "id": p.id,
            "title": p.title,
            "created_at": p.created_at,
            "views": p_views,
            "likes_count": l_cnt,
            "comments_count": c_cnt,
            "total_engagement": l_cnt + c_cnt
        })

    # Top posts (by views + likes + comments)
    top_posts = sorted(post_analytics_list, key=lambda x: (x["likes_count"] + x["comments_count"], x["views"]), reverse=True)[:5]
    recent_posts = post_analytics_list[:10]

    # 4. Timeline trend aggregation (last 7 to 30 days)
    timeline_days = days_filter if days_filter else 14
    timeline_dict = defaultdict(lambda: {"posts": 0, "views": 0, "likes": 0, "comments": 0})

    for d in range(timeline_days - 1, -1, -1):
        dt_key = (now - timedelta(days=d)).strftime("%Y-%m-%d")
        timeline_dict[dt_key] = {"posts": 0, "views": 0, "likes": 0, "comments": 0}

    for p in user_posts:
        dt_str = p.created_at.strftime("%Y-%m-%d") if p.created_at else None
        if dt_str in timeline_dict:
            timeline_dict[dt_str]["posts"] += 1
            timeline_dict[dt_str]["views"] += (p.views or 0)
            timeline_dict[dt_str]["likes"] += len(p.likes) if p.likes else 0
            timeline_dict[dt_str]["comments"] += len(p.comments) if p.comments else 0

    timeline_points = [
        {"date": k, "posts": v["posts"], "views": v["views"], "likes": v["likes"], "comments": v["comments"]}
        for k, v in sorted(timeline_dict.items())
    ]

    # 5. Engagement distribution across top posts
    dist_posts = user_posts[:8]
    distribution = {
        "post_titles": [p.title[:20] + "..." if len(p.title) > 20 else p.title for p in dist_posts],
        "likes_data": [len(p.likes) if p.likes else 0 for p in dist_posts],
        "comments_data": [len(p.comments) if p.comments else 0 for p in dist_posts],
        "views_data": [p.views or 0 for p in dist_posts]
    }

    # 6. Quota Usage
    plan = user.subscription_plan
    plan_name = plan.name if plan else "Basic"
    max_p = plan.max_posts if plan else 1
    max_l = plan.max_likes if plan else 5
    max_c = plan.max_comments if plan else 5

    posts_percent = 100.0 if max_p == -1 else min(round((total_posts / max_p) * 100, 1), 100.0)

    quota = {
        "plan_name": plan_name,
        "posts_used": total_posts,
        "posts_limit": max_p,
        "posts_percent": posts_percent,
        "likes_used": total_likes_given,
        "likes_limit": max_l,
        "comments_used": total_comments_made,
        "comments_limit": max_c
    }

    return {
        "user": user,
        "overview": overview,
        "quota": quota,
        "recent_posts": recent_posts,
        "top_posts": top_posts,
        "timeline": timeline_points,
        "distribution": distribution
    }


# -------------------------------------------------------------
# 1. JSON API ENDPOINTS (JWT SECURED)
# -------------------------------------------------------------
@router.get("/user/dashboard", response_model=UserDashboardResponse)
@router.get("/api/user/dashboard", response_model=UserDashboardResponse)
def get_user_dashboard(
    timeframe: Optional[str] = Query("all", description="Timeframe filter: '7d', '30d', or 'all'"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns personal analytics and activity metrics for the authenticated user.
    Strictly isolated: users only see their own activity data.
    """
    days = 7 if timeframe == "7d" else (30 if timeframe == "30d" else None)
    data = calculate_user_dashboard_data(current_user, db, days_filter=days)
    return data


@router.get("/user/dashboard/stats", response_model=UserStatsOverview)
def get_user_dashboard_stats(
    timeframe: Optional[str] = Query("all", description="Timeframe filter: '7d', '30d', or 'all'"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns lightweight summary stats overview for the authenticated user.
    """
    days = 7 if timeframe == "7d" else (30 if timeframe == "30d" else None)
    data = calculate_user_dashboard_data(current_user, db, days_filter=days)
    return data["overview"]


# -------------------------------------------------------------
# 2. INTERACTIVE CHART.JS USER DASHBOARD HTML PAGE
# -------------------------------------------------------------
@router.get("/dashboard", response_class=HTMLResponse)
@router.get("/user/dashboard/view", response_class=HTMLResponse)
def user_dashboard_html(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Renders the modern, interactive User Analytics Dashboard with Chart.js visualizations,
    KPI stat cards, dynamic API data loader, user switcher sandbox, and responsive layout.
    """
    users = db.query(User).order_by(User.id.desc()).limit(15).all()
    user_options_html = ""
    for u in users:
        plan_name = u.subscription_plan.name if u.subscription_plan else "Basic"
        u_token = create_access_token({"sub": u.username})
        user_options_html += f'<option value="{u.username}" data-token="{u_token}">{u.username} ({u.email}) - {plan_name} Tier</option>'

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Personal User Analytics & Activity Dashboard</title>
    <meta name="description" content="Personalized activity analytics and visual insights for Blog Management system users.">
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <!-- FontAwesome Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Chart.js 4.4 CDN -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        :root {{
            --bg-body: #0b0f19;
            --bg-card: rgba(18, 24, 38, 0.75);
            --bg-card-hover: rgba(28, 36, 56, 0.85);
            --border-color: rgba(255, 255, 255, 0.08);
            --border-glow: rgba(99, 102, 241, 0.35);
            --primary: #6366f1;
            --primary-gradient: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
            --secondary: #06b6d4;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --text-dim: #64748b;
            --glass-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.6), 0 0 15px rgba(99, 102, 241, 0.08);
            --transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Plus Jakarta Sans', sans-serif;
        }}

        body {{
            background-color: var(--bg-body);
            background-image: 
                radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.15) 0px, transparent 50%),
                radial-gradient(at 100% 0%, rgba(168, 85, 247, 0.15) 0px, transparent 50%),
                radial-gradient(at 50% 100%, rgba(6, 182, 212, 0.1) 0px, transparent 50%);
            background-attachment: fixed;
            color: var(--text-main);
            min-height: 100vh;
            padding-bottom: 60px;
        }}

        /* Navigation */
        .navbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 36px;
            background: rgba(11, 15, 25, 0.85);
            backdrop-filter: blur(16px);
            border-bottom: 1px solid var(--border-color);
            position: sticky;
            top: 0;
            z-index: 100;
        }}

        .brand {{
            display: flex;
            align-items: center;
            gap: 14px;
            text-decoration: none;
            color: var(--text-main);
        }}

        .brand-icon {{
            width: 42px;
            height: 42px;
            background: var(--primary-gradient);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
        }}

        .brand-text h1 {{
            font-size: 19px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }}

        .brand-text span {{
            font-size: 12px;
            color: var(--text-muted);
        }}

        .nav-actions {{
            display: flex;
            align-items: center;
            gap: 14px;
        }}

        .nav-link {{
            color: var(--text-muted);
            text-decoration: none;
            font-size: 13.5px;
            font-weight: 600;
            padding: 8px 14px;
            border-radius: 8px;
            transition: var(--transition);
        }}

        .nav-link:hover {{
            color: var(--text-main);
            background: rgba(255, 255, 255, 0.05);
        }}

        .btn-action {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 9px 18px;
            border-radius: 10px;
            font-size: 13.5px;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            border: none;
            transition: var(--transition);
        }}

        .btn-primary {{
            background: var(--primary-gradient);
            color: white;
            box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
        }}

        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5);
        }}

        .btn-secondary {{
            background: rgba(255, 255, 255, 0.08);
            color: var(--text-main);
            border: 1px solid var(--border-color);
        }}

        .btn-secondary:hover {{
            background: rgba(255, 255, 255, 0.12);
        }}

        /* Container */
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 28px 24px;
        }}

        /* Live User Switcher Panel */
        .auth-switch-panel {{
            background: var(--bg-card);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(99, 102, 241, 0.3);
            border-radius: 16px;
            padding: 16px 24px;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            margin-bottom: 24px;
            box-shadow: var(--glass-shadow);
        }}

        .auth-inputs {{
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
        }}

        .select-input, .text-input {{
            background: rgba(0, 0, 0, 0.4);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 9px 14px;
            border-radius: 10px;
            font-size: 13.5px;
            outline: none;
        }}

        .select-input:focus, .text-input:focus {{
            border-color: var(--primary);
        }}

        /* Profile Header */
        .control-bar {{
            background: var(--bg-card);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 20px 28px;
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 20px;
            margin-bottom: 24px;
            box-shadow: var(--glass-shadow);
        }}

        .user-profile-header {{
            display: flex;
            align-items: center;
            gap: 18px;
        }}

        .avatar-box {{
            width: 52px;
            height: 52px;
            border-radius: 14px;
            background: var(--primary-gradient);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            font-weight: 700;
            color: white;
            box-shadow: 0 4px 16px rgba(99, 102, 241, 0.3);
        }}

        .profile-info h2 {{
            font-size: 20px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .profile-info p {{
            font-size: 13.5px;
            color: var(--text-muted);
            margin-top: 3px;
        }}

        .badge-plan {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11.5px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .badge-basic {{ background: rgba(148, 163, 184, 0.15); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.3); }}
        .badge-premium {{ background: rgba(6, 182, 212, 0.15); color: #22d3ee; border: 1px solid rgba(6, 182, 212, 0.3); }}
        .badge-pro {{ background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); }}

        .timeframe-tabs {{
            display: flex;
            background: rgba(0, 0, 0, 0.3);
            padding: 4px;
            border-radius: 10px;
            border: 1px solid var(--border-color);
        }}

        .tab-btn {{
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 7px 15px;
            font-size: 13px;
            font-weight: 600;
            border-radius: 7px;
            cursor: pointer;
            transition: var(--transition);
        }}

        .tab-btn.active {{
            background: var(--primary);
            color: white;
            box-shadow: 0 2px 8px rgba(99, 102, 241, 0.4);
        }}

        /* KPI Cards */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
            gap: 20px;
            margin-bottom: 24px;
        }}

        .kpi-card {{
            background: var(--bg-card);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 22px 24px;
            transition: var(--transition);
            box-shadow: var(--glass-shadow);
            position: relative;
            overflow: hidden;
        }}

        .kpi-card:hover {{
            transform: translateY(-4px);
            border-color: var(--border-glow);
            box-shadow: 0 15px 30px -10px rgba(99, 102, 241, 0.2);
        }}

        .kpi-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: var(--primary-gradient);
            opacity: 0.8;
        }}

        .kpi-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}

        .kpi-title {{
            font-size: 13.5px;
            font-weight: 600;
            color: var(--text-muted);
        }}

        .kpi-icon {{
            width: 38px;
            height: 38px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 17px;
        }}

        .icon-purple {{ background: rgba(99, 102, 241, 0.15); color: #818cf8; }}
        .icon-pink {{ background: rgba(244, 63, 94, 0.15); color: #fb7185; }}
        .icon-cyan {{ background: rgba(6, 182, 212, 0.15); color: #38bdf8; }}
        .icon-amber {{ background: rgba(245, 158, 11, 0.15); color: #fbbf24; }}
        .icon-emerald {{ background: rgba(16, 185, 129, 0.15); color: #34d399; }}

        .kpi-value {{
            font-size: 28px;
            font-weight: 800;
            color: var(--text-main);
            letter-spacing: -0.5px;
            margin-bottom: 6px;
        }}

        .kpi-subtitle {{
            font-size: 12.5px;
            color: var(--text-dim);
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .kpi-subtitle .positive {{
            color: var(--success);
            font-weight: 600;
        }}

        /* Charts Layout */
        .charts-grid {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 24px;
            margin-bottom: 24px;
        }}

        @media (max-width: 1024px) {{
            .charts-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        .chart-card {{
            background: var(--bg-card);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            box-shadow: var(--glass-shadow);
        }}

        .chart-card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}

        .chart-title-group h3 {{
            font-size: 16.5px;
            font-weight: 700;
            color: var(--text-main);
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .chart-title-group p {{
            font-size: 12.5px;
            color: var(--text-muted);
            margin-top: 3px;
        }}

        .chart-container {{
            position: relative;
            height: 310px;
            width: 100%;
        }}

        .chart-container-donut {{
            position: relative;
            height: 270px;
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        /* Quota Utilization */
        .quota-card {{
            background: var(--bg-card);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            box-shadow: var(--glass-shadow);
        }}

        .quota-item {{
            margin-bottom: 16px;
        }}

        .quota-item-header {{
            display: flex;
            justify-content: space-between;
            font-size: 13.5px;
            margin-bottom: 6px;
        }}

        .quota-label {{
            font-weight: 600;
            color: var(--text-main);
        }}

        .quota-val {{
            font-weight: 700;
            color: var(--text-muted);
            font-family: 'JetBrains Mono', monospace;
        }}

        .progress-track {{
            height: 10px;
            background: rgba(255, 255, 255, 0.07);
            border-radius: 10px;
            overflow: hidden;
        }}

        .progress-bar-fill {{
            height: 100%;
            border-radius: 10px;
            background: var(--primary-gradient);
            transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        /* Table */
        .table-card {{
            background: var(--bg-card);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            box-shadow: var(--glass-shadow);
        }}

        .table-header-group {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
            margin-bottom: 20px;
        }}

        .search-box {{
            display: flex;
            align-items: center;
            gap: 10px;
            background: rgba(0, 0, 0, 0.25);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 8px 14px;
            width: 280px;
        }}

        .search-box input {{
            background: transparent;
            border: none;
            color: var(--text-main);
            font-size: 13.5px;
            outline: none;
            width: 100%;
        }}

        .custom-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13.5px;
        }}

        .custom-table th {{
            text-align: left;
            padding: 12px 16px;
            color: var(--text-muted);
            font-weight: 600;
            border-bottom: 1px solid var(--border-color);
            text-transform: uppercase;
            font-size: 11.5px;
            letter-spacing: 0.5px;
        }}

        .custom-table td {{
            padding: 14px 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            color: var(--text-main);
        }}

        .custom-table tr:hover td {{
            background: rgba(255, 255, 255, 0.02);
        }}

        .table-badge {{
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            font-family: 'JetBrains Mono', monospace;
        }}

        .badge-views {{ background: rgba(56, 189, 248, 0.15); color: #38bdf8; }}
        .badge-likes {{ background: rgba(251, 113, 133, 0.15); color: #fb7185; }}
        .badge-comments {{ background: rgba(168, 85, 247, 0.15); color: #c084fc; }}

        .toast {{
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: #1e293b;
            color: white;
            border: 1px solid var(--border-color);
            padding: 12px 20px;
            border-radius: 10px;
            font-size: 13.5px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            display: none;
            z-index: 1000;
        }}
    </style>
</head>
<body>

    <!-- Navigation -->
    <nav class="navbar">
        <a href="/dashboard" class="brand">
            <div class="brand-icon">
                <i class="fas fa-chart-line"></i>
            </div>
            <div class="brand-text">
                <h1>Blog Analytics Suite</h1>
                <span>Personal Activity & Performance Dashboard</span>
            </div>
        </a>

        <div class="nav-actions">
            <a href="/admin" class="nav-link"><i class="fas fa-shield-alt"></i> Admin Panel</a>
            <a href="/docs" target="_blank" class="nav-link"><i class="fas fa-book"></i> API Docs</a>
            <button class="btn-action btn-secondary" onclick="exportAnalyticsJSON()">
                <i class="fas fa-download"></i> Export JSON
            </button>
            <button class="btn-action btn-primary" onclick="refreshDashboardData()">
                <i class="fas fa-sync-alt" id="refresh-icon"></i> Refresh Live
            </button>
        </div>
    </nav>

    <!-- Main Container -->
    <main class="container">

        <!-- Live User Switcher Sandbox -->
        <section class="auth-switch-panel">
            <div style="display: flex; align-items: center; gap: 12px;">
                <i class="fas fa-user-circle" style="color: var(--primary); font-size: 24px;"></i>
                <div>
                    <strong style="font-size: 14px;">Interactive User / JWT Token Switcher:</strong>
                    <div style="font-size: 12px; color: var(--text-muted);">Switch active user from the database or enter a custom JWT token.</div>
                </div>
            </div>

            <div class="auth-inputs">
                <select id="user-select" class="select-input" onchange="onUserSelectChange()">
                    {user_options_html}
                </select>
                <input type="password" id="custom-token" class="text-input" placeholder="Custom JWT token..." style="width: 220px;" />
                <button class="btn-action btn-primary" onclick="loadSelectedUser()">
                    <i class="fas fa-arrow-right"></i> Load User
                </button>
            </div>
        </section>

        <!-- Header Profile & Timeframe Bar -->
        <section class="control-bar">
            <div class="user-profile-header">
                <div class="avatar-box" id="user-avatar">U</div>
                <div class="profile-info">
                    <h2>
                        <span id="display-username">Loading...</span>
                        <span id="display-plan" class="badge-plan badge-basic">Basic</span>
                    </h2>
                    <p id="display-email">user@techblog.com</p>
                </div>
            </div>

            <div class="timeframe-tabs">
                <button class="tab-btn active" onclick="setTimeframe('all', this)">All Time</button>
                <button class="tab-btn" onclick="setTimeframe('30d', this)">Last 30 Days</button>
                <button class="tab-btn" onclick="setTimeframe('7d', this)">Last 7 Days</button>
            </div>
        </section>

        <!-- KPI Summary Cards Grid -->
        <section class="kpi-grid">
            <!-- Total Posts -->
            <div class="kpi-card">
                <div class="kpi-header">
                    <span class="kpi-title">Total Posts</span>
                    <div class="kpi-icon icon-purple"><i class="fas fa-feather-alt"></i></div>
                </div>
                <div class="kpi-value" id="kpi-posts">0</div>
                <div class="kpi-subtitle">
                    <span class="positive"><i class="fas fa-check-circle"></i> Authored</span> by you
                </div>
            </div>

            <!-- Post Views -->
            <div class="kpi-card">
                <div class="kpi-header">
                    <span class="kpi-title">Total Post Views</span>
                    <div class="kpi-icon icon-cyan"><i class="fas fa-eye"></i></div>
                </div>
                <div class="kpi-value" id="kpi-views">0</div>
                <div class="kpi-subtitle">
                    <span class="positive"><i class="fas fa-chart-line"></i> Total Reads</span> on posts
                </div>
            </div>

            <!-- Likes Received -->
            <div class="kpi-card">
                <div class="kpi-header">
                    <span class="kpi-title">Likes Received</span>
                    <div class="kpi-icon icon-pink"><i class="fas fa-heart"></i></div>
                </div>
                <div class="kpi-value" id="kpi-likes-rec">0</div>
                <div class="kpi-subtitle">
                    <span>Avg <strong id="kpi-avg-likes">0.0</strong> / post</span>
                </div>
            </div>

            <!-- Comments Received -->
            <div class="kpi-card">
                <div class="kpi-header">
                    <span class="kpi-title">Comments Received</span>
                    <div class="kpi-icon icon-amber"><i class="fas fa-comments"></i></div>
                </div>
                <div class="kpi-value" id="kpi-comments-rec">0</div>
                <div class="kpi-subtitle">
                    <span>Avg <strong id="kpi-avg-comments">0.0</strong> / post</span>
                </div>
            </div>

            <!-- Engagement Rate -->
            <div class="kpi-card">
                <div class="kpi-header">
                    <span class="kpi-title">Engagement Rate</span>
                    <div class="kpi-icon icon-emerald"><i class="fas fa-fire"></i></div>
                </div>
                <div class="kpi-value" id="kpi-engagement-rate">0%</div>
                <div class="kpi-subtitle">
                    <span class="positive"><i class="fas fa-thumbs-up"></i> (Likes+Comments)/Views</span>
                </div>
            </div>
        </section>

        <!-- Charts Grid 1: Bar Chart & Donut Chart -->
        <section class="charts-grid">
            <!-- Bar Chart: Likes vs Comments per Post -->
            <div class="chart-card">
                <div class="chart-card-header">
                    <div class="chart-title-group">
                        <h3><i class="fas fa-chart-bar" style="color: #6366f1;"></i> Likes & Comments Distribution</h3>
                        <p>Engagement breakdown comparing likes, comments, and views per post</p>
                    </div>
                </div>
                <div class="chart-container">
                    <canvas id="barChartDistribution"></canvas>
                </div>
            </div>

            <!-- Doughnut Chart: Overall Engagement Mix -->
            <div class="chart-card">
                <div class="chart-card-header">
                    <div class="chart-title-group">
                        <h3><i class="fas fa-chart-pie" style="color: #a855f7;"></i> Engagement Mix</h3>
                        <p>Distribution of your overall platform interactions</p>
                    </div>
                </div>
                <div class="chart-container-donut">
                    <canvas id="doughnutChartRatio"></canvas>
                </div>
            </div>
        </section>

        <!-- Charts Grid 2: Timeline Line Chart & Quota Card -->
        <section class="charts-grid">
            <!-- Line Chart: Activity Trend Over Time -->
            <div class="chart-card">
                <div class="chart-card-header">
                    <div class="chart-title-group">
                        <h3><i class="fas fa-chart-area" style="color: #06b6d4;"></i> Activity Timeline</h3>
                        <p>Dynamic trend of views, likes & comments over time</p>
                    </div>
                </div>
                <div class="chart-container">
                    <canvas id="lineChartTimeline"></canvas>
                </div>
            </div>

            <!-- Subscription Plan Quota Utilization -->
            <div class="quota-card">
                <div class="chart-card-header">
                    <div class="chart-title-group">
                        <h3><i class="fas fa-gem" style="color: #f59e0b;"></i> Subscription Quota</h3>
                        <p>Current plan limit utilization</p>
                    </div>
                    <span class="badge-plan badge-premium" id="quota-plan-badge">Plan</span>
                </div>

                <div class="quota-item">
                    <div class="quota-item-header">
                        <span class="quota-label"><i class="fas fa-feather-alt"></i> Posts Allowed</span>
                        <span class="quota-val" id="quota-posts-text">0 / 1</span>
                    </div>
                    <div class="progress-track">
                        <div class="progress-bar-fill" id="quota-posts-bar" style="width: 0%;"></div>
                    </div>
                </div>

                <div class="quota-item">
                    <div class="quota-item-header">
                        <span class="quota-label"><i class="fas fa-heart"></i> Likes Given</span>
                        <span class="quota-val" id="quota-likes-text">0 / 5</span>
                    </div>
                    <div class="progress-track">
                        <div class="progress-bar-fill" id="quota-likes-bar" style="width: 0%; background: linear-gradient(135deg, #fb7185, #f43f5e);"></div>
                    </div>
                </div>

                <div class="quota-item">
                    <div class="quota-item-header">
                        <span class="quota-label"><i class="fas fa-comment"></i> Comments Made</span>
                        <span class="quota-val" id="quota-comments-text">0 / 5</span>
                    </div>
                    <div class="progress-track">
                        <div class="progress-bar-fill" id="quota-comments-bar" style="width: 0%; background: linear-gradient(135deg, #fbbf24, #f59e0b);"></div>
                    </div>
                </div>

                <div style="margin-top: 24px; padding: 14px; background: rgba(0,0,0,0.25); border-radius: 10px; font-size: 12.5px; color: var(--text-muted);">
                    <i class="fas fa-info-circle" style="color: var(--secondary);"></i> Need higher limits? Upgrade anytime via <code>/subscriptions/upgrade</code> API.
                </div>
            </div>
        </section>

        <!-- Post Analytics Table -->
        <section class="table-card">
            <div class="table-header-group">
                <div class="chart-title-group">
                    <h3><i class="fas fa-list-alt" style="color: #10b981;"></i> Post Performance Analytics</h3>
                    <p>Detailed breakdown for each article authored by you</p>
                </div>
                <div class="search-box">
                    <i class="fas fa-search" style="color: var(--text-dim);"></i>
                    <input type="text" id="postSearchInput" placeholder="Filter posts by title..." onkeyup="filterPostsTable()">
                </div>
            </div>

            <div style="overflow-x: auto;">
                <table class="custom-table" id="postsAnalyticsTable">
                    <thead>
                        <tr>
                            <th>Post ID</th>
                            <th>Title</th>
                            <th>Published Date</th>
                            <th>Views</th>
                            <th>Likes</th>
                            <th>Comments</th>
                            <th>Engagement</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody id="postsTableBody">
                        <tr>
                            <td colspan="8" style="text-align: center; color: var(--text-muted); padding: 24px;">
                                Loading analytics data...
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </section>

    </main>

    <!-- Toast Notification -->
    <div id="toast" class="toast">Data loaded successfully!</div>

    <!-- Chart.js Setup & Interactive JS Logic -->
    <script>
        let currentAuthToken = "";
        let currentTimeframe = "all";
        let latestDashboardData = null;

        // Chart instances
        let barChartInstance = null;
        let doughnutChartInstance = null;
        let lineChartInstance = null;

        // Setup Chart Defaults for Dark Theme
        Chart.defaults.color = '#94a3b8';
        Chart.defaults.font.family = "'Plus Jakarta Sans', sans-serif";
        Chart.defaults.font.size = 12;

        document.addEventListener("DOMContentLoaded", () => {{
            const sel = document.getElementById("user-select");
            if (sel && sel.options.length > 0) {{
                const opt = sel.options[0];
                currentAuthToken = opt.getAttribute("data-token") || "";
                document.getElementById("custom-token").value = currentAuthToken;
            }}
            fetchDashboard();
        }});

        function showToast(msg) {{
            const toast = document.getElementById("toast");
            toast.innerText = msg;
            toast.style.display = "block";
            setTimeout(() => {{ toast.style.display = "none"; }}, 3000);
        }}

        function onUserSelectChange() {{
            loadSelectedUser();
        }}

        function loadSelectedUser() {{
            const customInput = document.getElementById("custom-token").value.trim();
            const sel = document.getElementById("user-select");
            const opt = sel.options[sel.selectedIndex];

            if (opt && (!customInput || customInput.length < 20)) {{
                currentAuthToken = opt.getAttribute("data-token") || "";
                document.getElementById("custom-token").value = currentAuthToken;
            }} else if (customInput) {{
                currentAuthToken = customInput;
            }}
            fetchDashboard();
        }}

        async function setTimeframe(tf, btn) {{
            currentTimeframe = tf;
            document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            await fetchDashboard();
        }}

        async function refreshDashboardData() {{
            const icon = document.getElementById("refresh-icon");
            icon.classList.add("fa-spin");
            await fetchDashboard();
            setTimeout(() => {{ icon.classList.remove("fa-spin"); }}, 600);
            showToast("Dashboard analytics refreshed in real-time!");
        }}

        async function fetchDashboard() {{
            try {{
                const headers = {{}};
                if (currentAuthToken) {{
                    headers["Authorization"] = `Bearer ${{currentAuthToken}}`;
                }}

                const response = await fetch(`/user/dashboard?timeframe=${{currentTimeframe}}`, {{
                    headers: headers
                }});

                if (!response.ok) {{
                    if (response.status === 401) {{
                        document.getElementById("display-username").innerText = "Not Authenticated";
                        document.getElementById("display-email").innerText = "Please select a user above or enter a valid JWT token.";
                        return;
                    }}
                    throw new Error(`API Error: ${{response.status}}`);
                }}

                const data = await response.json();
                latestDashboardData = data;
                renderDashboard(data);
            }} catch (error) {{
                console.error("Failed to load dashboard data:", error);
            }}
        }}

        function renderDashboard(data) {{
            // 1. User Header
            const user = data.user;
            const overview = data.overview;
            const quota = data.quota;

            document.getElementById("display-username").innerText = user.username;
            document.getElementById("display-email").innerText = user.email;
            document.getElementById("user-avatar").innerText = user.username.charAt(0).toUpperCase();

            const planBadge = document.getElementById("display-plan");
            planBadge.innerText = quota.plan_name + " Plan";
            planBadge.className = `badge-plan badge-${{quota.plan_name.toLowerCase()}}`;

            const quotaBadge = document.getElementById("quota-plan-badge");
            quotaBadge.innerText = quota.plan_name;
            quotaBadge.className = `badge-plan badge-${{quota.plan_name.toLowerCase()}}`;

            // 2. KPI Cards
            document.getElementById("kpi-posts").innerText = overview.total_posts;
            document.getElementById("kpi-views").innerText = overview.total_post_views;
            document.getElementById("kpi-likes-rec").innerText = overview.total_likes_received;
            document.getElementById("kpi-avg-likes").innerText = overview.avg_likes_per_post;
            document.getElementById("kpi-comments-rec").innerText = overview.total_comments_received;
            document.getElementById("kpi-avg-comments").innerText = overview.avg_comments_per_post;
            document.getElementById("kpi-engagement-rate").innerText = overview.engagement_rate + "%";

            // 3. Quota Progress Bars
            const pLimit = quota.posts_limit === -1 ? "Unlimited" : quota.posts_limit;
            document.getElementById("quota-posts-text").innerText = `${{quota.posts_used}} / ${{pLimit}}`;
            document.getElementById("quota-posts-bar").style.width = `${{quota.posts_percent}}%`;

            const lLimit = quota.likes_limit === -1 ? "Unlimited" : quota.likes_limit;
            const lPercent = quota.likes_limit === -1 ? 100 : Math.min(100, (quota.likes_used / quota.likes_limit) * 100);
            document.getElementById("quota-likes-text").innerText = `${{quota.likes_used}} / ${{lLimit}}`;
            document.getElementById("quota-likes-bar").style.width = `${{lPercent}}%`;

            const cLimit = quota.comments_limit === -1 ? "Unlimited" : quota.comments_limit;
            const cPercent = quota.comments_limit === -1 ? 100 : Math.min(100, (quota.comments_used / quota.comments_limit) * 100);
            document.getElementById("quota-comments-text").innerText = `${{quota.comments_used}} / ${{cLimit}}`;
            document.getElementById("quota-comments-bar").style.width = `${{cPercent}}%`;

            // 4. Render Charts
            renderBarChart(data.distribution);
            renderDoughnutChart(overview);
            renderLineChart(data.timeline);

            // 5. Render Posts Table
            renderPostsTable(data.recent_posts);
        }}

        function renderBarChart(dist) {{
            const ctx = document.getElementById('barChartDistribution').getContext('2d');
            if (barChartInstance) barChartInstance.destroy();

            const labels = dist.post_titles.length ? dist.post_titles : ["No Posts Yet"];
            const likes = dist.likes_data.length ? dist.likes_data : [0];
            const comments = dist.comments_data.length ? dist.comments_data : [0];
            const views = dist.views_data.length ? dist.views_data : [0];

            barChartInstance = new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: labels,
                    datasets: [
                        {{
                            label: 'Likes',
                            data: likes,
                            backgroundColor: 'rgba(244, 63, 94, 0.75)',
                            borderColor: '#f43f5e',
                            borderWidth: 1.5,
                            borderRadius: 6
                        }},
                        {{
                            label: 'Comments',
                            data: comments,
                            backgroundColor: 'rgba(168, 85, 247, 0.75)',
                            borderColor: '#a855f7',
                            borderWidth: 1.5,
                            borderRadius: 6
                        }},
                        {{
                            label: 'Views',
                            data: views,
                            backgroundColor: 'rgba(6, 182, 212, 0.75)',
                            borderColor: '#06b6d4',
                            borderWidth: 1.5,
                            borderRadius: 6
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ position: 'top', labels: {{ boxWidth: 12, font: {{ weight: 600 }} }} }},
                        tooltip: {{
                            backgroundColor: '#1e293b',
                            titleColor: '#f8fafc',
                            bodyColor: '#cbd5e1',
                            borderColor: 'rgba(255,255,255,0.1)',
                            borderWidth: 1,
                            padding: 12
                        }}
                    }},
                    scales: {{
                        x: {{ grid: {{ display: false }} }},
                        y: {{ grid: {{ color: 'rgba(255, 255, 255, 0.05)' }}, beginAtZero: true }}
                    }}
                }}
            }});
        }}

        function renderDoughnutChart(overview) {{
            const ctx = document.getElementById('doughnutChartRatio').getContext('2d');
            if (doughnutChartInstance) doughnutChartInstance.destroy();

            const totalInteractions = overview.total_likes_received + overview.total_comments_received + overview.total_comments_made + overview.total_likes_given;
            const values = totalInteractions > 0 
                ? [overview.total_likes_received, overview.total_comments_received, overview.total_likes_given, overview.total_comments_made]
                : [1, 1, 1, 1];

            doughnutChartInstance = new Chart(ctx, {{
                type: 'doughnut',
                data: {{
                    labels: ['Likes Received', 'Comments Received', 'Likes Given', 'Comments Made'],
                    datasets: [{{
                        data: values,
                        backgroundColor: [
                            'rgba(244, 63, 94, 0.85)',
                            'rgba(168, 85, 247, 0.85)',
                            'rgba(99, 102, 241, 0.85)',
                            'rgba(245, 158, 11, 0.85)'
                        ],
                        borderColor: '#121826',
                        borderWidth: 3,
                        hoverOffset: 6
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ position: 'bottom', labels: {{ boxWidth: 10, font: {{ size: 11, weight: 600 }} }} }},
                        tooltip: {{
                            backgroundColor: '#1e293b',
                            titleColor: '#f8fafc',
                            bodyColor: '#cbd5e1',
                            borderColor: 'rgba(255,255,255,0.1)',
                            borderWidth: 1
                        }}
                    }},
                    cutout: '68%'
                }}
            }});
        }}

        function renderLineChart(timeline) {{
            const ctx = document.getElementById('lineChartTimeline').getContext('2d');
            if (lineChartInstance) lineChartInstance.destroy();

            const labels = timeline.map(t => t.date.slice(5));
            const views = timeline.map(t => t.views);
            const likes = timeline.map(t => t.likes);
            const comments = timeline.map(t => t.comments);

            lineChartInstance = new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: labels,
                    datasets: [
                        {{
                            label: 'Views Trend',
                            data: views,
                            borderColor: '#06b6d4',
                            backgroundColor: 'rgba(6, 182, 212, 0.12)',
                            tension: 0.35,
                            fill: true,
                            pointRadius: 4,
                            pointHoverRadius: 6
                        }},
                        {{
                            label: 'Likes Received',
                            data: likes,
                            borderColor: '#f43f5e',
                            backgroundColor: 'transparent',
                            borderDash: [5, 5],
                            tension: 0.3,
                            pointRadius: 3
                        }},
                        {{
                            label: 'Comments Received',
                            data: comments,
                            borderColor: '#a855f7',
                            backgroundColor: 'transparent',
                            tension: 0.3,
                            pointRadius: 3
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ position: 'top', labels: {{ boxWidth: 12, font: {{ weight: 600 }} }} }},
                        tooltip: {{
                            backgroundColor: '#1e293b',
                            padding: 12
                        }}
                    }},
                    scales: {{
                        x: {{ grid: {{ color: 'rgba(255, 255, 255, 0.04)' }} }},
                        y: {{ grid: {{ color: 'rgba(255, 255, 255, 0.05)' }}, beginAtZero: true }}
                    }}
                }}
            }});
        }}

        function renderPostsTable(posts) {{
            const tbody = document.getElementById("postsTableBody");
            if (!posts || posts.length === 0) {{
                tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 30px;">No posts created yet. Create a post using <code>POST /posts</code> to see detailed analytics!</td></tr>`;
                return;
            }}

            tbody.innerHTML = posts.map(p => {{
                const dateStr = new Date(p.created_at).toLocaleDateString('en-US', {{ month: 'short', day: 'numeric', year: 'numeric' }});
                return `
                <tr>
                    <td><code>#${{p.id}}</code></td>
                    <td><strong>${{p.title}}</strong></td>
                    <td style="color: var(--text-muted);">${{dateStr}}</td>
                    <td><span class="table-badge badge-views"><i class="fas fa-eye"></i> ${{p.views}}</span></td>
                    <td><span class="table-badge badge-likes"><i class="fas fa-heart"></i> ${{p.likes_count}}</span></td>
                    <td><span class="table-badge badge-comments"><i class="fas fa-comment"></i> ${{p.comments_count}}</span></td>
                    <td><strong>${{p.total_engagement}}</strong> interactions</td>
                    <td>
                        <a href="/posts/${{p.id}}" target="_blank" class="btn-action btn-secondary" style="padding: 4px 10px; font-size: 11.5px;">
                            <i class="fas fa-external-link-alt"></i> View
                        </a>
                    </td>
                </tr>
                `;
            }}).join('');
        }}

        function filterPostsTable() {{
            const filter = document.getElementById("postSearchInput").value.toLowerCase();
            const rows = document.querySelectorAll("#postsTableBody tr");
            rows.forEach(row => {{
                const text = row.innerText.toLowerCase();
                row.style.display = text.includes(filter) ? "" : "none";
            }});
        }}

        function exportAnalyticsJSON() {{
            if (!latestDashboardData) return;
            const jsonStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(latestDashboardData, null, 2));
            const downloadAnchor = document.createElement('a');
            downloadAnchor.setAttribute("href", jsonStr);
            downloadAnchor.setAttribute("download", `user_analytics_${{latestDashboardData.user.username}}.json`);
            document.body.appendChild(downloadAnchor);
            downloadAnchor.click();
            downloadAnchor.remove();
            showToast("Exported JSON analytics report!");
        }}
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
